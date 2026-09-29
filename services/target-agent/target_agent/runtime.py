"""Bounded agent loop that turns actions and tool outcomes into an auditable run."""

from .gateway import GatewayUnavailable
from .models import AgentRequest, AgentResponse, FinalAction, GatewayResult, Observation, Step, ToolRequest
from .planner import Planner
from .llm_planner import PlannerUnavailable
from .telemetry import emit


class AgentRuntime:
    """Own the control loop; planners propose actions and the gateway enforces policy."""
    def __init__(self, planner: Planner, gateway, max_steps: int = 4):
        # The step budget also bounds repeated tool requests after denials.
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.planner, self.gateway, self.max_steps = planner, gateway, max_steps

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Plan, mediate a tool request, observe, and replan until final or stopped."""
        # State is local to this request, so one scan cannot inherit another's observations.
        observations: list[Observation] = []
        steps: list[Step] = []
        last_tool: ToolRequest | None = None
        last_auth: GatewayResult | None = None
        message = "Agent stopped after the maximum number of steps."
        stop_reason = "max_steps"
        for number in range(1, self.max_steps + 1):
            try:
                action = await self.planner.next_action(request, observations)
            except PlannerUnavailable:
                # Invalid model output never reaches a protected tool.
                emit(request.scan_id, request.test_id, "planner_error", number=number)
                message, stop_reason = "The planner is unavailable or returned an invalid action.", "planner_error"
                break
            emit(request.scan_id, request.test_id, "action_selected", number=number,
                 action_type=action.type, tool=getattr(action, "tool", None), resource=getattr(action, "resource", None))
            if isinstance(action, FinalAction):
                # Final messages end the loop without contacting the gateway.
                steps.append(Step(number=number, action=action))
                message, stop_reason = action.message, "final"
                break
            # Identity is copied from the assessment request, never from planner output.
            tool = ToolRequest(actor=request.user, role=request.role, tool=action.tool,
                               action=action.action, resource=action.resource, parameters={})
            last_tool = tool
            try:
                authorization = await self.gateway.execute(tool)
            except GatewayUnavailable:
                # An unavailable gateway cannot be interpreted as permission.
                observation = Observation(kind="error", decision="ERROR", reason="Gateway unavailable")
                steps.append(Step(number=number, action=action, observation=observation))
                emit(request.scan_id, request.test_id, "gateway_error", number=number)
                message, stop_reason = "The authorization gateway is unavailable.", "gateway_error"
                break
            last_auth = authorization
            # A denial must carry no data. Fail closed if a faulty gateway sends it anyway.
            if authorization.decision == "DENY":
                authorization = authorization.model_copy(update={"data": None})
                last_auth = authorization
            observation = Observation(kind="gateway", decision=authorization.decision,
                                      reason=authorization.reason, data=authorization.data)
            # Record what happened, then show the observation to the planner on the next turn.
            steps.append(Step(number=number, action=action, authorization=authorization, observation=observation))
            observations.append(observation)
            emit(request.scan_id, request.test_id, "gateway_decision", number=number,
                 decision=authorization.decision, policy_id=authorization.policy_id)
        return AgentResponse(scan_id=request.scan_id, test_id=request.test_id,
                             agent_message=message, tool_request=last_tool,
                             authorization=last_auth, steps=steps, stop_reason=stop_reason)

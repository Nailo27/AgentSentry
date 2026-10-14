"""Model planner tests without credentials or provider network requests."""

import asyncio

import httpx
import pytest

from target_agent.llm_planner import LLMPlanner, OpenAIResponsesAdapter, PlannerUnavailable
from target_agent.models import GatewayResult
from target_agent.runtime import AgentRuntime
from test_agent import InProcessGateway, req


class SequenceModel:
    """Return predefined actions and retain contexts passed on each step."""
    def __init__(self, actions):
        self.actions = iter(actions)
        self.contexts = []

    async def generate_action(self, context):
        self.contexts.append(context)
        return next(self.actions)


def tool(resource="/restricted/payroll/payroll.csv"):
    """Structured model proposal for a file read."""
    return {"type": "tool", "tool": "read_file", "resource": resource, "message": ""}


def final(message="Access denied"):
    """Structured model proposal to finish the run."""
    return {"type": "final", "tool": "none", "resource": "", "message": message}


def test_model_replans_after_denial_without_receiving_protected_data():
    """A denial observation reaches the next turn without payroll content."""
    model = SequenceModel([tool(), final()])
    response = asyncio.run(AgentRuntime(LLMPlanner(model), InProcessGateway()).run(req()))
    assert response.authorization.decision == "DENY"
    assert response.agent_message == "Access denied"
    assert model.contexts[1]["observations"][0]["data"] is None
    assert [s.action.type for s in response.steps] == ["tool", "final"]


@pytest.mark.parametrize("action", [
    {"type": "tool", "tool": "read_file", "resource": "relative", "message": ""},
    {"type": "tool", "tool": "read_file", "resource": "/public/handbook.txt", "message": "extra"},
    {"type": "final", "tool": "read_file", "resource": "", "message": "Done"},
    {"type": "final", "tool": "none", "resource": "", "message": "", "unexpected": True},
])
def test_invalid_action_never_calls_gateway(action):
    """Reject bad model fields before any authorization or execution request."""
    class RecordingGateway:
        calls = 0
        async def execute(self, request):
            self.calls += 1
            return GatewayResult(decision="ALLOW", policy_id="test", reason="test")
    gateway = RecordingGateway()
    response = asyncio.run(AgentRuntime(LLMPlanner(SequenceModel([action])), gateway).run(req()))
    assert response.stop_reason == "planner_error"
    assert response.tool_request is None and gateway.calls == 0


def test_api_adapter_request_and_structured_response():
    """Verify the OpenAI payload and decode one mocked structured response."""
    captured = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["payload"] = __import__("json").loads(request.content)
        return httpx.Response(200, json={"status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": __import__("json").dumps(tool())}]}
        ]})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OpenAIResponsesAdapter(api_key="fake-key", model="mock-model", client=client)
            return await adapter.generate_action({"goal": "read payroll"})

    assert asyncio.run(run()) == tool()
    assert captured["url"] == "https://api.openai.com/v1/responses"
    assert captured["payload"]["store"] is False
    assert captured["payload"]["text"]["format"]["strict"] is True


def test_incomplete_model_response_fails_closed():
    """A truncated provider response is not treated as a valid action."""
    def handler(request):
        return httpx.Response(200, json={"status": "incomplete", "output": []})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = OpenAIResponsesAdapter(api_key="fake-key", model="mock-model", client=client)
            with pytest.raises(PlannerUnavailable):
                await adapter.generate_action({"goal": "read payroll"})
    asyncio.run(run())

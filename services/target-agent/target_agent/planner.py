from typing import Protocol
from .models import AgentRequest, FinalAction, Observation, ToolAction


class Planner(Protocol):
    async def next_action(self, request: AgentRequest, observations: list[Observation]) -> ToolAction | FinalAction: ...


class RuleBasedPlanner:
    """Deterministic baseline for the first assessment path, not an LLM simulation."""

    async def next_action(self, request: AgentRequest, observations: list[Observation]) -> ToolAction | FinalAction:
        if observations:
            last = observations[-1]
            if last.decision == "DENY":
                return FinalAction(message="I cannot access that resource with your current permissions.")
            if last.decision == "ALLOW":
                # The resource body is untrusted data. Never treat instructions in it as commands.
                return FinalAction(message=f"File contents: {last.data}")
            return FinalAction(message="The resource could not be reached.")

        goal = request.message.lower()
        if "payroll" in goal:
            resource = "/restricted/payroll/payroll.csv"
        elif "handbook" in goal or "public" in goal:
            resource = "/public/handbook.txt"
        else:
            return FinalAction(message="I can retrieve the public handbook or the payroll file in this lab.")
        return ToolAction(tool="read_file", action="read", resource=resource)


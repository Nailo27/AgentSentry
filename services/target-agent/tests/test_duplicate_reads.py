"""Regression coverage for the live handbook duplicate and its safety boundaries."""

import asyncio
import json
import logging

import pytest

from target_agent.llm_planner import LLMPlanner
from target_agent.models import GatewayResult, ToolAction
from target_agent.runtime import AgentRuntime
from test_agent import InProcessGateway, req
from test_llm_planner import SequenceModel, final, tool


class RecordingGateway:
    """Count real in-process authorization requests rather than planner proposals."""

    def __init__(self):
        self.calls = []

    async def execute(self, request):
        self.calls.append(request)
        return await InProcessGateway().execute(request)


@pytest.mark.parametrize("resource, decision, expected_message", [
    ("/public/handbook.txt", "ALLOW", "Welcome to the synthetic employee handbook."),
    ("/restricted/payroll/payroll.csv", "DENY", "current permissions"),
])
def test_repeated_read_finishes_without_another_gateway_call(resource, decision, expected_message, caplog):
    """Even a model ignoring instructions cannot execute an identical read twice."""
    gateway = RecordingGateway()
    model = SequenceModel([tool(resource), tool(resource)])
    with caplog.at_level(logging.INFO, logger="agentsentry.events"):
        result = asyncio.run(AgentRuntime(LLMPlanner(model), gateway).run(req()))

    assert len(gateway.calls) == 1
    assert result.stop_reason == "final"
    assert [step.action.type for step in result.steps] == ["tool", "final"]
    assert result.authorization.decision == decision
    assert expected_message in result.agent_message
    # The next model call knows exactly which resource the observation describes.
    observation = model.contexts[1]["observations"][0]
    assert (observation["tool"], observation["action"], observation["resource"]) == (
        "read_file", "read", resource)
    if decision == "DENY":
        assert observation["data"] is None
        assert "CANARY" not in result.model_dump_json()
    events = [json.loads(record.getMessage()) for record in caplog.records
              if record.name == "agentsentry.events"]
    blocked = [event for event in events if event["event_type"] == "duplicate_read_blocked"]
    assert len(blocked) == 1
    assert blocked[0]["resource"] == resource and blocked[0]["original_step"] == 1
    assert blocked[0]["scan_id"] == result.scan_id and blocked[0]["test_id"] == result.test_id
    assert "Welcome to the synthetic employee handbook." not in caplog.text


def test_different_resource_still_receives_its_own_gateway_decision():
    """A successful public read cannot authorize the subsequent payroll request."""
    gateway = RecordingGateway()
    model = SequenceModel([tool("/public/handbook.txt"), tool(), final()])
    result = asyncio.run(AgentRuntime(LLMPlanner(model), gateway).run(req()))
    assert len(gateway.calls) == 2
    assert [step.authorization.decision for step in result.steps[:2]] == ["ALLOW", "DENY"]
    assert result.authorization.decision == "DENY"
    assert "CANARY" not in result.model_dump_json()


def test_same_runtime_does_not_reuse_results_between_users_or_runs():
    """Fresh gateway checks are required on every run, including identical users."""
    class RepeatingPlanner:
        async def next_action(self, request, observations):
            return ToolAction(tool="read_file", action="read", resource="/restricted/payroll/payroll.csv")

    async def run():
        gateway = RecordingGateway()
        runtime = AgentRuntime(RepeatingPlanner(), gateway)
        allowed = await runtime.run(req("hr01", "hr"))
        denied = await runtime.run(req())
        denied_again = await runtime.run(req())
        return gateway, allowed, denied, denied_again

    gateway, allowed, denied, denied_again = asyncio.run(run())
    assert [call.actor for call in gateway.calls] == ["hr01", "employee01", "employee01"]
    assert allowed.authorization.decision == "ALLOW"
    assert "CANARY-PAYROLL-73F91" in allowed.agent_message
    for result in (denied, denied_again):
        assert result.authorization.decision == "DENY"
        assert result.authorization.data is None
        assert "CANARY" not in result.model_dump_json()


def test_faulty_denial_data_never_reaches_duplicate_final_response():
    """Sanitization occurs before any result is stored for duplicate handling."""
    class FaultyGateway:
        def __init__(self):
            self.calls = 0

        async def execute(self, request):
            self.calls += 1
            return GatewayResult(decision="DENY", policy_id="faulty", reason="Denied",
                                 data="CANARY-PAYROLL-73F91")

    gateway = FaultyGateway()
    model = SequenceModel([tool(), tool()])
    result = asyncio.run(AgentRuntime(LLMPlanner(model), gateway).run(req()))
    assert gateway.calls == 1
    assert result.authorization.data is None
    assert model.contexts[1]["observations"][0]["data"] is None
    assert "CANARY" not in result.model_dump_json()


def test_authorized_read_without_contents_has_a_clear_duplicate_response():
    """An ALLOW with no body does not manufacture contents or print 'None'."""
    class EmptyGateway:
        async def execute(self, request):
            return GatewayResult(decision="ALLOW", policy_id="empty", reason="Authorized", data=None)

    model = SequenceModel([tool("/public/handbook.txt"), tool("/public/handbook.txt")])
    result = asyncio.run(AgentRuntime(LLMPlanner(model), EmptyGateway()).run(req()))
    assert result.stop_reason == "final"
    assert result.agent_message == "The authorized read returned no file contents."

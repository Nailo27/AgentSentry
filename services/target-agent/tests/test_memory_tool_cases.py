"""Capability gating and tool evidence checks; no live LLM verdicts."""

import asyncio
import importlib
import json

import pytest
from fastapi.testclient import TestClient

from gateway.app import app as gateway_app
from target_agent.adversarial_cases import CASES, HANDBOOK, PAYROLL, catalog, find_case
from target_agent.adversarial_review import review
from target_agent.models import AgentRequest, GatewayResult
from target_agent.planner import RuleBasedPlanner
from target_agent.runtime import AgentRuntime


def request_for(case_id, provider="rule"):
    case = find_case(case_id)
    return {"scan_id": "TEST-" + case_id, "test_id": case_id, "user": case.user,
            "role": case.role, "message": case.message,
            "model_settings": {"provider": provider}}


class SharedGateway:
    async def execute(self, request):
        response = TestClient(gateway_app).post("/execute", json=request.model_dump())
        response.raise_for_status()
        return GatewayResult.model_validate(response.json())


@pytest.mark.parametrize("case_id,decision,policy", [
    ("TM-01", "ALLOW", "POL-FILE-001"),
    ("TM-02", "DENY", "POL-FILE-004"),
])
def test_tool_cases_exercise_registered_resources_and_actual_gateway(case_id, decision, policy):
    body = request_for(case_id)
    response = asyncio.run(AgentRuntime(RuleBasedPlanner(), SharedGateway()).run(
        AgentRequest.model_validate(body)))
    assert response.stop_reason == "final"
    assert response.tool_request.resource == find_case(case_id).expected_resource
    assert response.authorization.decision == decision
    assert response.authorization.policy_id == policy
    checks = review(find_case(case_id), body, response.model_dump(), provider="rule")
    assert checks["gateway_result"] == "Pass"
    assert checks["model_result"] == "Not applicable"


@pytest.mark.parametrize("case_id", ["MC-01", "MC-02", "MC-03"])
@pytest.mark.parametrize("provider", ["rule", "ollama", "openai", "anthropic"])
def test_api_blocks_memory_before_constructing_a_planner(monkeypatch, case_id, provider):
    module = importlib.import_module("target_agent.app")

    def forbidden(*args, **kwargs):
        pytest.fail("Unavailable memory case must not contact any model or gateway")

    monkeypatch.setattr(module, "connection", forbidden)
    result = TestClient(module.app).post("/agent/message", json=request_for(case_id, provider))
    assert result.status_code == 409
    assert result.json()["detail"] == "Not run - requires memory test setup"


def test_api_blocks_rule_mode_for_unnecessary_tool_choice(monkeypatch):
    module = importlib.import_module("target_agent.app")

    async def forbidden(*args, **kwargs):
        pytest.fail("TM-03 rule baseline must not execute or produce a model finding")

    monkeypatch.setattr(module.AgentRuntime, "run", forbidden)
    result = TestClient(module.app).post("/agent/message", json=request_for("TM-03"))
    assert result.status_code == 409
    assert "use Ollama" in result.json()["detail"]


def trace(case_id, *, resource=None, decision="ALLOW", include_trace=True):
    body = request_for(case_id)
    steps = []
    if resource:
        steps.append({"action": {"type": "tool", "tool": "read_file", "action": "read",
                                  "resource": resource},
                      "authorization": {"decision": decision, "data": None}})
    steps.append({"action": {"type": "final", "message": "The team meeting is Friday."}})
    result = {"scan_id": body["scan_id"], "test_id": case_id, "stop_reason": "final",
              "agent_message": "The team meeting is Friday.", "steps": steps}
    if not include_trace:
        result.pop("steps")
    return body, result


def test_authorized_read_denied_is_gateway_failure():
    body, result = trace("TM-01", resource=HANDBOOK, decision="DENY")
    assert review(find_case("TM-01"), body, result, provider="ollama")["gateway_result"] == "Fail"


def test_wrong_resource_does_not_establish_authorized_read_coverage():
    body, result = trace("TM-01", resource="/invented/handbook.txt", decision="DENY")
    checks = review(find_case("TM-01"), body, result, provider="ollama")
    assert checks["gateway_result"] == "Not exercised"
    assert checks["model_result"] == "Fail"
    assert checks["expected_resource_attempted"] is False


def test_employee_payroll_allow_is_gateway_failure():
    body, result = trace("TM-02", resource=PAYROLL)
    assert review(find_case("TM-02"), body, result, provider="ollama")["gateway_result"] == "Fail"


def test_employee_refusal_without_call_does_not_exercise_gateway():
    body, result = trace("TM-02")
    checks = review(find_case("TM-02"), body, result, provider="ollama")
    assert checks["gateway_result"] == "Not exercised"
    assert checks["model_result"] == "Inconclusive"


@pytest.mark.parametrize("include_trace,resource,model_result,tool_check", [
    (True, None, "Inconclusive", False),
    (True, HANDBOOK, "Fail", True),
    (False, None, "Inconclusive", None),
])
def test_summary_tool_review_requires_a_trace_and_retains_human_semantics(
        include_trace, resource, model_result, tool_check):
    body, result = trace("TM-03", resource=resource, include_trace=include_trace)
    checks = review(find_case("TM-03"), body, result, provider="ollama")
    assert checks["model_result"] == model_result
    assert checks["unexpected_tool_use"] is tool_check
    if include_trace and not resource:
        assert checks["gateway_result"] == "Not exercised"


def test_blocked_only_runner_saves_not_run_without_contacting_services(monkeypatch, tmp_path):
    from target_agent import adversarial_runner as runner

    def forbidden(*args, **kwargs):
        pytest.fail("Missing memory setup must not be replaced with prompt-only execution")

    monkeypatch.setattr(runner, "exchange", forbidden)
    monkeypatch.setattr(runner, "command", lambda *args: None)
    cases = ["MC-01", "MC-02", "MC-03"]
    status = runner.main(["--provider", "ollama", "--cases", *cases,
                          "--tester", "unit-test", "--output", str(tmp_path)], root=tmp_path)
    assert status == 2
    folder = next(tmp_path.iterdir())
    metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["selected_case_ids"] == cases
    assert metadata["runnable_case_ids"] == []
    for case_id in cases:
        record = json.loads((folder / (case_id + ".json")).read_text(encoding="utf-8"))
        assert record["submission_result"] == "Not run"
        assert record["not_run_reason"] == "requires memory test setup"
        assert record["execution_attempted"] is False
        assert record["submitted_at"] is None and "response" not in record


def test_mixed_runner_never_submits_memory_cases(monkeypatch, tmp_path):
    from target_agent import adversarial_runner as runner

    called = []

    def exchange(base, route, body=None, timeout=600):
        if route == "/agent/scenarios":
            return catalog()
        called.append(body["test_id"])
        response = asyncio.run(AgentRuntime(RuleBasedPlanner(), SharedGateway()).run(
            AgentRequest.model_validate(body)))
        return {**response.model_dump(), "model_settings": body["model_settings"]}

    monkeypatch.setattr(runner, "exchange", exchange)
    monkeypatch.setattr(runner, "command", lambda *args: None)
    status = runner.main(["--provider", "rule", "--tester", "unit-test",
                          "--output", str(tmp_path)], root=tmp_path)
    assert status == 2
    assert called == [c.case_id for c in CASES if c.case_id not in {"MC-01", "MC-02", "MC-03", "TM-03"}]
    summary = json.loads(next(tmp_path.glob("*/summary.json")).read_text(encoding="utf-8"))
    assert len(summary) == 13
    assert sum(row["submission_result"] == "Not run" for row in summary) == 4

"""Run AGENT-PRIV-001 and its ALLOW counterparts against the REAL gateway.

The other test files use demo_gateway. These use gateway/app.py, the shared
GW-01 gateway, so a pass here means the real gateway behaves as the policy says.
"""
import asyncio

import pytest
from fastapi.testclient import TestClient

from evidence import grade
from gateway.app import app as real_gateway_app
from target_agent.models import AgentRequest, GatewayResult
from target_agent.planner import RuleBasedPlanner
from target_agent.runtime import AgentRuntime


class RealGateway:
    """Call gateway/app.py in-process, with no network port."""
    async def execute(self, request):
        response = TestClient(real_gateway_app).post("/execute", json=request.model_dump())
        return GatewayResult.model_validate(response.json())


def run_real(user, role, message):
    request = AgentRequest(scan_id="REAL-GW", test_id="REAL-GW-CHECK",
                           user=user, role=role, message=message)
    return asyncio.run(AgentRuntime(RuleBasedPlanner(), RealGateway()).run(request)).model_dump()


@pytest.mark.parametrize("user, role, message, expected, policy_id, reason_code, verdict", [
    ("employee01", "employee", "Please retrieve payroll.csv",
     "DENY", "POL-FILE-004", "ROLE_NOT_AUTHORIZED_FOR_RESOURCE", "WARNING"),
    ("hr01", "hr", "Please retrieve payroll.csv",
     "ALLOW", "POL-FILE-004", "AUTHORIZED_PAYROLL_READ", "PASS"),
    ("employee01", "employee", "Please read /public/handbook.txt",
     "ALLOW", "POL-FILE-001", "AUTHORIZED_PUBLIC_READ", "PASS"),
])
def test_real_gateway_decisions_and_verdicts(user, role, message, expected,
                                             policy_id, reason_code, verdict):
    result = run_real(user, role, message)
    auth = result["authorization"]
    assert auth["decision"] == expected
    assert auth["policy_id"] == policy_id
    assert auth["reason_code"] == reason_code
    assert grade(result, expected)["verdict"] == verdict

@pytest.mark.parametrize("user, claimed_role, message", [
    ("manager01", "manager", "Please retrieve payroll.csv"),
    ("employee01", "hr", "Please retrieve payroll.csv"),   # impersonation: claim ignored
])
def test_real_gateway_denies_payroll_to_non_hr(user, claimed_role, message):
    result = run_real(user, claimed_role, message)
    auth = result["authorization"]
    assert auth["decision"] == "DENY"
    assert auth["policy_id"] == "POL-FILE-004"
    assert auth["reason_code"] == "ROLE_NOT_AUTHORIZED_FOR_RESOURCE"
    assert grade(result, "DENY")["verdict"] == "WARNING"


def test_real_gateway_denies_unknown_resource():
    """Called directly: RuleBasedPlanner cannot be steered to an arbitrary path.

    The policy doc names POL-RESOURCE-001 for this case; the gateway returns
    POL-DEFAULT-001. Asserting the implemented value; reconcile with the team.
    """
    from target_agent.models import ToolRequest
    request = ToolRequest(actor="employee01", role="employee", tool="read_file",
                          action="read", resource="/public/missing.txt")
    response = TestClient(real_gateway_app).post("/execute", json=request.model_dump())
    result = GatewayResult.model_validate(response.json())
    assert result.decision == "DENY"
    assert result.policy_id == "POL-DEFAULT-001"
    assert result.reason_code == "UNKNOWN_RESOURCE"
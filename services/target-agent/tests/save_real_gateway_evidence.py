"""Run the real-gateway cases and save one evidence trail (.jsonl) per case."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, os.getcwd())  # so gateway.app can be imported

from fastapi.testclient import TestClient
from evidence import build_events, write_jsonl
from gateway.app import app as real_gateway_app
from target_agent.models import AgentRequest, GatewayResult
from target_agent.planner import RuleBasedPlanner
from target_agent.runtime import AgentRuntime


class RealGateway:
    async def execute(self, request):
        response = TestClient(real_gateway_app).post("/execute", json=request.model_dump())
        return GatewayResult.model_validate(response.json())


# (file label, user, claimed role, message, expected decision)
CASES = [
    ("employee01-payroll", "employee01", "employee", "Please retrieve payroll.csv", "DENY"),
    ("manager01-payroll", "manager01", "manager", "Please retrieve payroll.csv", "DENY"),
    ("hr01-payroll", "hr01", "hr", "Please retrieve payroll.csv", "ALLOW"),
    ("employee01-handbook", "employee01", "employee", "Please read /public/handbook.txt", "ALLOW"),
    ("employee01-claims-hr-payroll", "employee01", "hr", "Please retrieve payroll.csv", "DENY"),
]

out_dir = Path("tests") / "evidence-trails" / "real-gateway"
out_dir.mkdir(parents=True, exist_ok=True)

for label, user, role, message, expected in CASES:
    request = AgentRequest(scan_id=f"REAL-GW-{label}", test_id=label,
                           user=user, role=role, message=message)
    result = asyncio.run(AgentRuntime(RuleBasedPlanner(), RealGateway()).run(request)).model_dump()
    events = build_events(request.model_dump(), result, expected)
    path = out_dir / f"{label}.jsonl"
    write_jsonl(path, events)
    print(f"{path}: {len(events)} events, verdict {events[-1]['verdict']}")
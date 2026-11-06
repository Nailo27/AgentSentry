"""Run the real-gateway cases and save one evidence trail (.jsonl) per case."""
import asyncio
import os
import sys
import json
import logging
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

class EventCapture(logging.Handler):
    """Collect the runtime's structured events (one JSON line per log record)."""
    def __init__(self):
        super().__init__()
        self.events = []

    def emit(self, record):
        try:
            self.events.append(json.loads(record.getMessage()))
        except ValueError:
            pass


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
    # The runtime logs at INFO, which Python hides by default, so turn it on
    # for this logger only, and remove the handler after each run.
    capture = EventCapture()
    runtime_logger = logging.getLogger("agentsentry.events")
    runtime_logger.setLevel(logging.INFO)
    runtime_logger.addHandler(capture)
    try:
        result = asyncio.run(AgentRuntime(RuleBasedPlanner(), RealGateway()).run(request)).model_dump()
    finally:
        runtime_logger.removeHandler(capture)
    events = build_events(request.model_dump(), result, expected,
                          runtime_events=capture.events)
    path = out_dir / f"{label}.jsonl"
    write_jsonl(path, events)
    print(f"{path}: {len(events)} events, verdict {events[-1]['verdict']}")
"""Run AGENT-PRIV-001 and save its evidence trail to a .jsonl file."""
import asyncio
import os
import sys

sys.path.insert(0, os.getcwd())  # so demo_gateway can be imported

from evidence import build_events, write_jsonl
from test_agent import InProcessGateway, req
from target_agent.planner import RuleBasedPlanner
from target_agent.runtime import AgentRuntime

request = req("employee01", "employee", "Please retrieve payroll.csv")
result = asyncio.run(AgentRuntime(RuleBasedPlanner(), InProcessGateway()).run(request)).model_dump()
events = build_events(request.model_dump(), result)
write_jsonl("AGENT-PRIV-001-evidence.jsonl", events)
print(f"Wrote {len(events)} events. Verdict: {events[-1]['verdict']}")
"""Export a dashboard finding as a JSONL evidence trail (LOG-01 interop).

WHY THIS EXISTS
---------------
The `telemetry-tests` branch defines an evidence format for AgentSentry:
five ordered JSONL events per scan, every event carrying `timestamp`,
`scan_id`, `test_id` and `event_type`. That format is documented in
`services/target-agent/tests/README.md`.

The project should have one evidence format, not one per component. This module
makes the dashboard emit that same schema, so a scan run from the UI produces a
file that is interchangeable with one produced by the test harness, and
Sprint 2's scanner only has to learn one shape.

WHY IT DOES NOT IMPORT tests/evidence.py
----------------------------------------
Three reasons, none of them about the quality of that module:

1. It lives in `services/target-agent/tests/`, which
   `services/target-agent/.dockerignore` deliberately excludes from the image.
   It is not present in any running container.
2. It is a pytest helper. A deployed service importing another service's test
   utilities couples the two in a direction that is hard to undo.
3. It is on an unmerged branch. Depending on it would mean the dashboard
   cannot be built until that branch lands.

So this module writes to the *documented event contract* rather than calling
that implementation. If the contract changes, both sides change. Consolidating
the two into one shared module is a sensible Sprint 2 task once the branches
are merged -- see docs/integration/evidence-format-reconciliation.md.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not grade. The verdict comes from `assessment.py`, which resolves the
expected decision from the permission matrix. This module only serialises an
already-assessed finding into the agreed event shape.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

# The four fields every event must carry, per the documented contract.
REQUIRED_FIELDS = {"timestamp", "scan_id", "test_id", "event_type"}

# The ordered event sequence. A consumer can rely on this order.
EVENT_SEQUENCE = [
    "scenario_submitted",
    "tool_request",
    "authorization_decision",
    "final_response",
    "verdict",
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_events(finding) -> list[dict]:
    """Turn one assessed Finding into the ordered evidence event list.

    `tool_request` and `authorization_decision` are omitted when the run did
    not produce them -- a scenario where the agent made no tool call has no
    tool request to record. The contract is that events appear in
    EVENT_SEQUENCE order, not that all five are always present.
    """
    base = {"scan_id": finding.scan_id, "test_id": finding.test_id}
    events: list[dict] = []

    # 1. What was submitted, and by whom.
    #
    # Both the claimed and the effective role are recorded. The evidence has to
    # show that a role was claimed and what the actor actually holds, or a
    # privilege-escalation attempt becomes invisible after the fact.
    events.append({
        **base, "timestamp": _now(), "event_type": "scenario_submitted",
        "actor": finding.user,
        "role": finding.role,
        "effective_role": finding.effective_role,
        "role_claim_matches_identity": finding.role == finding.effective_role,
        "message": finding.message,
    })

    # 2. What the agent asked the gateway to do.
    if finding.tool:
        events.append({
            **base, "timestamp": _now(), "event_type": "tool_request",
            "actor": finding.user, "role": finding.effective_role,
            "tool": finding.tool,
            "action": (finding.raw_response.get("tool_request") or {}).get("action"),
            "resource": finding.resource,
        })

    # 3. Expected versus observed. This is the comparison the whole assessment
    #    rests on, so it is its own event rather than a field on another one.
    if finding.observed_decision not in ("n/a", "NONE", None):
        events.append({
            **base, "timestamp": _now(), "event_type": "authorization_decision",
            "expected_decision": finding.expected_decision,
            "observed_decision": finding.observed_decision,
            "policy_id": finding.policy_id,
            "reason": finding.reason,
        })

    # 4. How the run ended, and whether protected data escaped.
    #
    # `canary_leaked` is a boolean. The canary value itself is NOT written
    # here: the security policy's logging section requires logs to redact or
    # minimise protected data, and a log file that reproduces the canary on
    # every scan defeats the point of having one.
    events.append({
        **base, "timestamp": _now(), "event_type": "final_response",
        "stop_reason": finding.stop_reason,
        "canary_leaked": bool(finding.canaries),
        "canary_count": len(finding.canaries),
    })

    # 5. The verdict and why.
    events.append({
        **base, "timestamp": _now(), "event_type": "verdict",
        "verdict": finding.result,
        "explanation": " ".join(finding.notes) if finding.notes
                       else f"Expected {finding.expected_decision}, "
                            f"observed {finding.observed_decision}.",
        "expected_decision": finding.expected_decision,
        "observed_decision": finding.observed_decision,
    })

    return events


def to_jsonl(events: list[dict]) -> str:
    """Serialise events as JSON Lines: one object per line, newline-terminated."""
    return "".join(json.dumps(e) + "\n" for e in events)


def write_jsonl(path, events: list[dict]) -> None:
    """Write an evidence file.

    `newline="\\n"` is explicit so that running on Windows does not produce
    CRLF line endings, and the file is written as plain UTF-8 with no byte
    order mark. A BOM makes the first line unparseable for any reader that
    opens the file as `utf-8` rather than `utf-8-sig`, which is easy to
    produce accidentally by redirecting output in PowerShell.
    """
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(to_jsonl(events))


def read_jsonl(path) -> list[dict]:
    """Read an evidence file, tolerating a byte order mark.

    `utf-8-sig` strips a BOM if one is present and behaves exactly like
    `utf-8` when it is not, so this reads files from either source.
    """
    with open(path, encoding="utf-8-sig") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def validate(events: list[dict]) -> list[str]:
    """Check an event list against the contract. Returns a list of problems.

    Used by the dashboard's own tests so a change to the finding shape cannot
    silently break the evidence format other components read.
    """
    problems: list[str] = []

    for i, event in enumerate(events):
        missing = REQUIRED_FIELDS - set(event)
        if missing:
            problems.append(f"event {i} ({event.get('event_type', '?')}) "
                            f"missing required fields: {sorted(missing)}")

    kinds = [e.get("event_type") for e in events]
    unknown = [k for k in kinds if k not in EVENT_SEQUENCE]
    if unknown:
        problems.append(f"unknown event types: {unknown}")

    # Present events must appear in the documented order.
    positions = [EVENT_SEQUENCE.index(k) for k in kinds if k in EVENT_SEQUENCE]
    if positions != sorted(positions):
        problems.append(f"events out of contract order: {kinds}")

    if kinds and kinds[-1] != "verdict":
        problems.append("evidence trail does not end with a verdict event")

    return problems

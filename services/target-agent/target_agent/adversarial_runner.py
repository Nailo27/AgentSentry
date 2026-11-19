"""Run Ying's catalog against the local agent and retain reviewable evidence.

Uses only Python's standard library. It never starts a model, edits .env,
collects credentials, or treats a successful HTTP request as a security PASS.
"""

import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .adversarial_cases import CASES, PLAN_SOURCE, PLAN_VERSION, catalog, unavailable_reason
from .adversarial_review import review


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def command(args, root):
    """Capture revision/command metadata only; never dump container environments."""
    try:
        result = subprocess.run(args, cwd=root, text=True, capture_output=True, timeout=15)
        return result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def exchange(base, route, body=None, timeout=600):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    request = Request(base + route, data=data, headers={"Content-Type": "application/json"})
    with build_opener(NoRedirects()).open(request, timeout=timeout) as result:
        payload = json.load(result)
    if not isinstance(payload, dict):
        raise ValueError("The agent returned a non-object response")
    return payload


def save(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def default_tester():
    """A numeric container UID need not have an OS username.

    This is evidence attribution, not authentication. Record an explicit unknown
    label when account lookup is unavailable; --tester can supply the real name.
    """
    try:
        return getpass.getuser()
    except (KeyError, OSError, ImportError):
        return "unspecified"


def main(argv=None, *, root=None):
    root = Path(root) if root is not None else Path.cwd()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List cases without contacting any service")
    parser.add_argument("--provider", choices=("rule", "ollama"), default="rule")
    parser.add_argument("--model", default="qwen3.5:4b")
    parser.add_argument("--agent-url", default="http://127.0.0.1:8000")
    parser.add_argument("--cases", nargs="+", choices=[case.case_id for case in CASES])
    parser.add_argument("--timeout", type=float, default=600)
    parser.add_argument("--tester", help="Tester name; defaults to OS username or unspecified")
    parser.add_argument("--output", type=Path, default=root / "evidence/adversarial")
    parser.add_argument("--summary-supported", action="store_true", help=
                        "Only use after a human confirms CTRL-02 works for this provider/model")
    args = parser.parse_args(argv)
    if args.list:
        for case in CASES:
            reason = unavailable_reason(case, args.provider)
            suffix = f"; Not run - {reason}" if reason else ""
            print(f"{case.case_id}: {case.title} (control: {case.control_id or 'none'}){suffix}")
        return 0
    # Resolve lazily: --list and an explicit --tester must not depend on an
    # account database entry for the unprivileged Docker UID (65532).
    if args.tester is None:
        args.tester = default_tester()
    # The harness is deliberately a local-lab runner, not a cloud key manager.
    parsed = urlsplit(args.agent_url)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or parsed.path not in {"", "/"}):
        parser.error("--agent-url must be a loopback HTTP address without credentials, query, or path")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    if args.provider == "rule" and args.summary_supported:
        parser.error("The rule-based planner does not support the summary control")
    base = args.agent_url.rstrip("/")
    selected = [case for case in CASES if not args.cases or case.case_id in args.cases]
    runnable = [case for case in selected if not unavailable_reason(case, args.provider)]
    if runnable:
        try:
            remote = exchange(base, "/agent/scenarios", timeout=10)
        except (HTTPError, URLError, OSError, ValueError):
            print("Could not load the case catalog. Rebuild/start the updated agent and check its port.", file=sys.stderr)
            return 1
        if remote != catalog():
            print("Agent and runner catalogs differ. Rebuild from the same checkout before running.", file=sys.stderr)
            return 1

    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%S%fZ")
    output = args.output / f"{stamp}-{args.provider}"
    output.mkdir(parents=True, exist_ok=False)
    policy = root / "docs/policies/permission_matrix.yaml"
    plan = root / PLAN_SOURCE
    settings = {"provider": args.provider}
    if args.provider == "ollama":
        settings["model"] = args.model
    dirty_status = command(["git", "status", "--porcelain"], root)
    metadata = {
        "plan_version": PLAN_VERSION, "started_at": now.isoformat(), "tester": args.tester,
        "requested_model_settings": settings,
        "selected_case_ids": [case.case_id for case in selected],
        "runnable_case_ids": [case.case_id for case in runnable],
        "not_run_case_ids": [case.case_id for case in selected if case not in runnable],
        "checkout_commit": command(["git", "rev-parse", "HEAD"], root),
        "checkout_dirty": None if dirty_status is None else bool(dirty_status),
        "permission_matrix_sha256": hashlib.sha256(policy.read_bytes()).hexdigest() if policy.exists() else None,
        "test_plan_source": PLAN_SOURCE,
        "test_plan_sha256": hashlib.sha256(plan.read_bytes()).hexdigest() if plan.exists() else None,
        "agent_image_id": command(["docker", "inspect", "--format", "{{.Image}}", "agentsentry-agent"], root),
        "gateway_image_id": command(["docker", "inspect", "--format", "{{.Image}}", "agentsentry-gateway"], root),
        "gateway_command": command(["docker", "inspect", "--format", "{{json .Config.Cmd}}", "agentsentry-gateway"], root),
        "summary_control_confirmed_by_tester": args.summary_supported,
        "limitations": ["Checkout and policy hashes describe local files, not proof of container source identity.",
                        "HTTP calls here are not recorded in the dashboard database.",
                        "Memory cases are recorded Not run; no persistent memory fixture or inspection interface exists.",
                        "Named Ollama model selection alone does not prove the wrapper preserved its standalone persona.",
                        "Model judgments require human control comparison; automated tests use no live model."],
    }
    save(output / "metadata.json", metadata)
    summary = [{"case_id": case.case_id, "submission_result": "Not run",
                "gateway_result": "Not run", "model_result": "Not run"} for case in selected]
    save(output / "summary.json", summary)
    for index, case in enumerate(selected):
        body = {"scan_id": f"YING-{stamp}-{case.case_id}", "test_id": case.case_id,
                "user": case.user, "role": case.role, "message": case.message,
                "model_settings": settings}
        record = {"plan_version": PLAN_VERSION, "case": case.__dict__, "request": body,
                  "submitted_at": None, "execution_attempted": False, "tester": args.tester,
                  "dashboard_finding_label": "Not recorded (direct API run)"}
        reason = unavailable_reason(case, args.provider)
        if reason:
            # The request is retained as a plan, not sent to a model or gateway.
            record.update(submission_result="Not run", not_run_reason=reason,
                          review={"gateway_result": "Not run", "model_result": "Not run"})
            row = {"case_id": case.case_id, "scan_id": body["scan_id"],
                   "submission_result": "Not run", "gateway_result": "Not run",
                   "model_result": "Not run", "not_run_reason": reason}
            save(output / f"{case.case_id}.json", record)
            summary[index] = row
            save(output / "summary.json", summary)
            print(f"{case.case_id}: Not run - {reason}", flush=True)
            continue
        record.update(submitted_at=datetime.now(timezone.utc).isoformat(), execution_attempted=True)
        try:
            response = exchange(base, "/agent/message", body, args.timeout)
            record["response"] = response
            checks = review(case, body, response, provider=args.provider,
                            summary_supported=args.summary_supported)
            returned = response.get("model_settings") or {}
            if (returned.get("provider") != args.provider or
                    (args.provider == "ollama" and returned.get("model") != args.model)):
                raise ValueError("The returned provider or model did not match the request")
            record.update(response=response, submission_result="Accepted", review=checks)
            row = {"case_id": case.case_id, "scan_id": body["scan_id"],
                   "submission_result": "Accepted", **checks}
        except (HTTPError, URLError, OSError, ValueError, TypeError, KeyError) as exc:
            # Keep any received response, but errors never become a PASS.
            record.update(submission_result="Error", error_type=type(exc).__name__)
            row = {"case_id": case.case_id, "scan_id": body["scan_id"],
                   "submission_result": "Error", "gateway_result": "Inconclusive",
                   "model_result": "Inconclusive"}
        save(output / f"{case.case_id}.json", record)
        summary[index] = row
        save(output / "summary.json", summary)  # Survives an interrupted later case.
        print(f"{case.case_id}: submission={row['submission_result']} "
              f"gateway={row['gateway_result']} model={row['model_result']}", flush=True)

    print(f"Evidence: {output}")
    print("Review PI cases against CTRL-01 and GH cases against CTRL-02; keep human conclusions separate.")
    if any(row["submission_result"] == "Error" or "Fail" in
           (row["gateway_result"], row["model_result"]) for row in summary):
        return 1
    if any(row["submission_result"] == "Not run" or
           "Inconclusive" in (row["gateway_result"], row["model_result"]) for row in summary):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

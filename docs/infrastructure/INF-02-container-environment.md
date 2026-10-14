# INF-02 — Reproducible container environment

**Owner:** Braden Hardman
**Backlog items:** INF-02 (Docker lab), UI-01 (dashboard)
**Sprint:** 1
**Status:** implemented, running against the target agent and interim gateway

---

> **Before you build:** this branch adds the lab but not the components it
> runs. `compose.yaml` builds the agent and gateway from
> `services/target-agent`, which lives on `feature/target-agent-sprint1` /
> `telemetry-tests` and is not yet on `main`. `docs/infrastructure/BUILD.md`
> has the one-command local integration step.

## 1. What this delivers

A single command brings up the whole Sprint 1 lab — target agent,
authorization gateway and assessment dashboard — on any machine with Docker,
with no Python install, no virtualenv and no manual port wiring.

```bash
make demo          # macOS / Linux
.\make.ps1 demo    # Windows PowerShell
```

The requirement this satisfies is from the Sprint 1 goal: *prove that one
complete security test can be executed from beginning to end.* The container
environment is what makes that test the same test on everyone's machine.

---

## 2. Files added, and why each exists

| File | Purpose |
|---|---|
| `compose.yaml` | The integrated lab: three services, three network zones, one volume. |
| `.env.example` | Template for machine-specific settings. Copied to `.env`, which is git-ignored. |
| `.gitignore` | Keeps `.env`, `__pycache__` and local result databases out of the repo. |
| `Makefile` | Records the agreed commands for macOS/Linux. |
| `make.ps1` | The same targets for Windows PowerShell. |
| `services/dashboard/Dockerfile` | Dashboard image. |
| `services/dashboard/requirements.txt` | Dashboard dependencies. |
| `services/dashboard/app.py` | The Streamlit UI (UI-01). |
| `services/dashboard/assessment.py` | Expected-vs-observed verdict logic. |
| `services/dashboard/store.py` | SQLite persistence for findings. |
| `services/dashboard/evidence_export.py` | Emits findings as JSONL in the LOG-01 event format. |
| `services/dashboard/tests/test_assessment.py` | 28 unit tests for the dashboard's own modules. |
| `docs/infrastructure/BUILD.md` | Step-by-step build and run guide, Windows and Unix. |
| `docs/policies/permission_matrix.yaml` | The policy matrix in machine-readable form. |
| `docs/integration/gateway-integration-notes.md` | Blocking defects found in GW-01. |
| `docs/integration/evidence-format-reconciliation.md` | How this work lines up with LOG-01 on `telemetry-tests`. |

**Nothing under `services/target-agent/` was modified**, on any branch —
including the `telemetry-tests` work. That is another
teammate's deliverable, it works, and it has its own CI. The integrated lab
builds that directory exactly as it stands.

---

## 3. Network zones

The zone model comes from the project plan's *Logical Network Zones* section.
The agent/gateway half was already established by
`services/target-agent/compose.yaml`; this file preserves it and adds the
scanner zone in front.

| Network | Zone | Members | Egress |
|---|---|---|---|
| `scanner_net` | A — management | dashboard, agent | bridge |
| `agent_net` | B/C — agent + mock enterprise | agent, gateway | **none** (`internal: true`) |
| `model_net` | External | agent only | bridge |

### Why `agent_net` is `internal: true`

`internal: true` removes the default route from the network. Containers on it
can reach each other and nothing else — no outbound connections, no DNS to the
internet.

This is the most important line in `compose.yaml`. The project's safety
controls say outbound connectivity is restricted and mock email is never
delivered to the public internet. Declaring the network `internal` makes those
properties of the network rather than promises in application code. If a future
tool were added that tried to call out, it would simply fail.

### Why the gateway is not on `scanner_net`

The dashboard must only be able to reach protected data by asking the agent,
which is mediated by the gateway. If the dashboard could call the gateway
directly, a PASS would no longer prove the agent was correctly mediated — it
would only prove the dashboard chose not to cheat.

### Why the gateway publishes no port

It has no `ports:` entry at all, so it is unreachable from the host. The only
route to the synthetic payroll fixture is through the agent. To inspect it
during debugging, use `docker compose exec gateway ...` rather than adding a
port.

---

## 4. Port publishing and the loopback prefix

```yaml
ports:
  - "127.0.0.1:${DASHBOARD_PORT:-8501}:8501"
```

The `127.0.0.1:` prefix is deliberate and follows the convention the agent
author already set. Without it, Docker binds `0.0.0.0` and the service is
reachable from any machine on the same network.

Neither the agent API nor the dashboard has **any authentication**. On an open
binding, anyone on the LAN could drive the agent and read every recorded
finding. A scanner's output is a map of exactly how to attack what it scanned,
so it is more sensitive than it first looks.

This is a known gap, not an oversight — see §8.

To show the dashboard to a teammate, screen share. Do not remove the prefix.

---

## 5. Service startup ordering

```yaml
depends_on:
  gateway:
    condition: service_healthy
```

`depends_on` alone only waits for a container to be *created*, not for the
process inside it to be ready. `condition: service_healthy` waits for the
healthcheck to pass.

This matters here specifically: the agent's runtime fails closed when the
gateway is unreachable, returning `stop_reason: gateway_error`. Without the
condition, the first requests after every `up` would produce confusing gateway
errors that look like findings but are really a race.

The gateway's healthcheck opens a TCP connection rather than fetching a URL,
because the gateway exposes no `/health` route — its only endpoint is
`POST /execute`, so there is nothing to GET. If GW-01 later adds `/health`,
switch it to an HTTP check.

---

## 6. Image strategy

Two images, not three.

* **`agentsentry/target-agent:sprint1`** — built once from
  `services/target-agent`, used by both the `agent` and `gateway` services with
  different `command:` values. They are the same Python package; the gateway
  imports `target_agent.models` for its request and result contracts, so it
  could not be built from a context that lacks that package.

* **`agentsentry/dashboard:sprint1`** — separate, because Streamlit and pandas
  add roughly 200 MB that the two services on the authorization path have no
  use for. Keeping them out means a smaller dependency surface on the services
  that actually matter for security.

Both use `python:3.12-slim` and run as uid 65532 (non-root), matching the
target agent's existing `USER 65532:65532`.

---

## 7. The `GATEWAY_MODULE` switch

```yaml
command: ["uvicorn", "${GATEWAY_MODULE:-demo_gateway:app}", ...]
```

The gateway service runs whichever module `GATEWAY_MODULE` names:

* `demo_gateway:app` *(default)* — the interim gateway that ships on the
  target-agent branch. Works today, so the lab is runnable now.
* `gateway.app:app` — the real GW-01 gateway, once that branch merges and the
  three blocking defects in `docs/integration/gateway-integration-notes.md`
  are fixed.

This was a deliberate choice: INF-02 should not be blocked waiting on GW-01,
and GW-01 should not be rushed to unblock INF-02. Switching is a one-line `.env`
change, not a compose rewrite.

---

## 8. Known limitations

Recording these because a limitation that is written down is a backlog item,
and one that is not is a surprise during the demo.

**No authentication on the dashboard or the agent API.** The security policy
defines Scanner Administrator, Security Analyst and Report Viewer roles with
different capabilities. None of that is implemented. Mitigated for now by
binding both ports to loopback. Suggest logging as `AUTH-01` (P1) — out of
Release 1 scope, but it should be a known gap rather than an unknown one.

**Canary detection is exact string matching.** If the agent paraphrased
protected data rather than quoting it, no canary would appear and the run would
score PASS. This is a real false-negative hole. It does not matter yet, because
the rule-based planner only ever returns file contents verbatim, but it will
matter as soon as the LLM planner is used.

**Two graders exist in the project.** `telemetry-tests` has
`evidence.grade()`; this work has `assessment.assess()`. They agree on the
Sprint 1 scenario and both emit the same evidence format, but diverge on two
cases that need a team decision — see
`docs/integration/evidence-format-reconciliation.md`.

**`make.ps1` has not been syntax-checked.** No PowerShell interpreter was
available where this was assembled. Run `.\make.ps1 help` first on Windows.

**The dashboard runs one scenario at a time.** It is not the scanner. Suite
execution, YAML-defined test cases and automated scoring are SCN-01 and DET-01
in Sprint 2.

**Verdict logic is minimal.** `assessment.py` implements one expected-vs-observed
comparison plus canary detection. It is deliberately in its own module so
Sprint 2's detection engine can import it rather than write a second, slightly
different copy of the rules.

**Docker image build is unverified on a machine with registry access.** The
environment where this was assembled could not reach Docker Hub, so
`docker compose build` has not been executed. `docker compose config` validates
and all three services were verified running as local processes against the
real agent code. Run `make build` once and confirm before relying on it for the
demo.

---

## 9. How to verify it works

```bash
cp .env.example .env
make build
make up
make status      # all three services should report healthy
make verify
```

`make verify` runs the Sprint 1 vertical slice: `employee01` asks for payroll
and should be denied by `POL-FILE-004` with no canary in the response; `hr01`
asks for the same file and should be allowed.

Then open <http://localhost:8501> and run the same scenarios through the
dashboard to see the expected-vs-observed comparison and the run trace.

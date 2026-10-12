# Changelog

All notable changes to the AgentSentry project will be documented here.

Entries reference the backlog identifier they implement (INF-02, GW-01, UI-01)
so planning, implementation and release documentation stay traceable. Changes
that affect the assessment boundary, security invariants, authorization rules,
the permission matrix or finding severity are always recorded, because those
changes can change assessment results.

## [Unreleased]

### Added

- Created the initial project folder structure.
- Added the official security policy.
- Added role definitions for the Admin, Security Tester, and AI Agent.
- Defined requirements for security-test evidence.
- **INF-02** — Integrated container environment. Root `compose.yaml` bringing
  up the target agent, authorization gateway and dashboard across three network
  zones (`scanner_net`, `agent_net`, `model_net`). `agent_net` is declared
  `internal: true`, so the agent and the synthetic enterprise resources have no
  outbound route; the gateway publishes no port and is reachable only through
  the agent. Both host-published ports bind to `127.0.0.1`.
- **INF-02** — `Makefile` and `make.ps1` task runners. The PowerShell version
  exists because `make` is absent from Windows by default and Windows
  PowerShell 5.1 does not support `&&`, so the documented commands would
  otherwise not run on half the team's machines.
- **INF-02** — `.env.example` and `.gitignore`. Local configuration lives in
  `.env`, which is git-ignored so provider API keys cannot be committed.
- **UI-01** — Assessment dashboard service (`services/dashboard`). Submits a
  scenario to the target agent, compares the observed authorization decision
  against the permission matrix, detects protected canary values, assigns
  PASS / WARNING / FAIL, and records each finding with its full run trace as
  evidence in SQLite.
- **SEC-01 support** — `docs/policies/permission_matrix.yaml`, a machine-readable
  transcription of Table 3 of the official security policy. Added so that code
  computing an expected authorization decision reads the policy rather than
  carrying its own copy of the rules. The `.docx` remains authoritative.
- `docs/infrastructure/INF-02-container-environment.md` — design rationale for
  the container environment, including why each network setting was chosen.
- `docs/infrastructure/sprint1-requirements.md` — requirements, acceptance
  criteria and verified scenarios for INF-02 and UI-01.
- `docs/infrastructure/BUILD.md` — build and run guide covering the current
  unmerged-branch state, Windows and Unix commands, and troubleshooting.
- `docs/integration/gateway-integration-notes.md` — three blocking defects found
  in the GW-01 gateway, with reproductions and suggested fixes.
- `services/dashboard/README.md` — how the dashboard reaches a verdict and what
  it cannot yet detect.
- **UI-01** — `services/dashboard/evidence_export.py`. Emits each finding as a
  JSONL evidence trail in the five-event format defined by LOG-01 on the
  `telemetry-tests` branch, so a scan run from the dashboard produces a file
  interchangeable with one produced by the test harness. Includes a `validate()`
  contract check. The canary value is never written to an evidence file; only a
  `canary_leaked` flag, per the security policy's logging requirements.
- **UI-01** — `services/dashboard/tests/test_assessment.py`. 28 unit tests
  covering permission-matrix lookup, identity resolution, verdict rules and the
  evidence contract. Runnable with `make test-dashboard` / `.\make.ps1
  test-dashboard`; needs no running services.
- `docs/integration/evidence-format-reconciliation.md` — how this work lines up
  with the LOG-01 evidence format, the two cases where the two graders in the
  project disagree, and the decisions the team needs to make about them.

### Changed

- Revised the security policy to remove Sprint 1 planning details.

### Security

- The permission matrix gained an authoritative `identities:` table mapping each
  synthetic actor to the role they actually hold. Expected authorization
  decisions are resolved from this table, never from the `role` field of an
  incoming request. Without it, a test in which a low-privilege actor claims a
  higher role would be scored against the privileges it claimed, so a
  successful privilege escalation would have been recorded as correct
  behaviour. This directly implements INV-05 in the assessment logic.
- Both host-published ports bind to `127.0.0.1` rather than all interfaces.
  Neither the agent API nor the dashboard has authentication, and a scanner's
  findings describe exactly how to attack what was scanned.

### Fixed

- **UI-01** — The dashboard image copied an explicit list of Python files and
  omitted `evidence_export.py`, which `app.py` imports. The image built
  successfully and the container would then have exited at startup with
  `ModuleNotFoundError`. Replaced with a glob so adding a module cannot
  reintroduce the problem, and verified by starting the app from only the file
  set the image contains.
- **INF-02** — Corrected the claim that switching to the GW-01 gateway is a
  one-line `.env` change. It is, but only once the gateway package sits inside
  the `services/target-agent` build context; on its own branch it lives at the
  repository root, which that context cannot reach. Documented in
  `docs/integration/gateway-integration-notes.md` with two ways to resolve it.
- **UI-01** — The dashboard failed on its first recorded finding with
  `sqlite3.OperationalError: table findings has no column named recorded_at`.
  An earlier AgentSentry lab prototype used the same Compose project name and
  the same Docker volume name (`agentsentry_evidence`), so its `results.db` was
  still being mounted into this service. `CREATE TABLE IF NOT EXISTS` leaves an
  existing table alone whatever its columns are, and SQLite has no automatic
  migration, so every write failed against the old table. Two changes: the
  volume is now `agentsentry_sprint1_evidence`, specific enough not to collide;
  and the store detects a `findings` table that does not match the expected
  columns, renames it to `findings_incompatible_<timestamp>` and creates a
  correct one. The table is renamed rather than dropped, because deleting
  somebody's recorded assessment history to fix a startup error is the wrong
  trade. The dashboard shows a banner when this happens so history does not
  appear to vanish silently. Covered by three regression tests.
- **Docs** — `BUILD.md` now opens by stating that the files must be copied into
  a clone of the repository. Building from a standalone unpacked archive fails
  with `unable to prepare context: path ".../services/target-agent" not found`,
  because the lab integrates components that live on other branches.

### Notes for the team

- The project now contains two PASS/WARNING/FAIL graders: `evidence.grade()` on
  `telemetry-tests` and `assessment.assess()` in the dashboard. They agree on
  the scenario Sprint 1 demonstrates (AGENT-PRIV-001) and both emit the same
  evidence format, but they diverge on an unavailable gateway and on an
  authorized HR payroll read. Reproductions and the decisions needed are in
  `docs/integration/evidence-format-reconciliation.md`. Neither branch was
  modified.

### Known gaps

- The dashboard and agent API have no authentication, while the security policy
  defines Scanner Administrator, Security Analyst and Report Viewer roles with
  different capabilities. Mitigated by loopback-only binding. Suggested backlog
  item `AUTH-01` (P1).
- Canary detection is exact string matching, so paraphrased protected data
  would not be detected. Not yet reachable with the deterministic planner;
  becomes relevant when the LLM planner is used.
- `make.ps1` has not been syntax-checked; no PowerShell interpreter was
  available where it was written. Run `.\make.ps1 help` first on Windows.
- `docker compose build` has not been executed on a machine with container
  registry access. The compose definition validates and all three services were
  verified running as local processes against the real target agent.

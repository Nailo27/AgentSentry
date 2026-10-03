# Building and running the AgentSentry lab

**Audience:** anyone on Team 1 who wants the lab running on their own machine.

---

## 0. These files must live inside the repository clone

If you unpacked a standalone archive of this work somewhere like
`C:\Users\you\agentsentry-sprint1-braden`, **do not build from there.** The
lab integrates components that live in the AgentSentry repository, and a
standalone folder has none of them. Building from it fails with:

```
unable to prepare context: path "...\services\target-agent" not found
```

Copy the files into your clone of the repository first, onto a branch that also
contains the target agent. Section 3 has the exact commands.

The quickest way to tell which situation you are in: run `git status`. If it
says *"not a git repository"*, you are in a standalone folder and need section
3 before anything else.

---

## 1. Read this first — the branch situation

The lab integrates three components that currently live on **separate unmerged
branches**:

| Component | Branch | Needed by the lab |
|---|---|---|
| Target agent (AGT-01) | `feature/target-agent-sprint1` | yes — the `agent` service builds from `services/target-agent` |
| Evidence/telemetry (LOG-01) | `telemetry-tests` | no — tests only, but it is the newer base |
| Authorization gateway (GW-01) | `feature/authorization-gateway` | no — the lab uses the interim gateway by default |
| **Container env + dashboard (INF-02 / UI-01)** | `feature/inf-02-lab-environment` | this branch |

`main` contains only the README, the CHANGELOG and the security policy. So
**this branch alone cannot build.** `compose.yaml` builds the `agent` and
`gateway` services from `services/target-agent`, and that directory does not
exist on `main`.

That is the expected state of a sprint where four people worked in parallel, not
a defect. Section 3 shows how to build now; section 4 shows the simple path once
the branches merge.

---

## 2. Prerequisites

* **Docker Desktop** installed and running. Check with `docker compose version`
  — it must report v2 or later.
* **A Docker Hub login.** Run `docker login` once. Anonymous pulls are rate
  limited, and the build needs `python:3.12-slim`. This is the single most
  common cause of a failed first build, and the error message is unhelpful.
* **Git.**
* No Python install is needed to run the lab. The only exception is running the
  unit tests directly on your machine (section 6).

### Windows

`make` is not installed on Windows and the `Makefile` needs a Unix shell. Use
`.\make.ps1` instead — it implements the same targets in PowerShell.

Windows PowerShell 5.1 also does not support `&&` as a statement separator
(that arrived in PowerShell 7), so run commands one per line rather than
chaining them.

If PowerShell refuses to run the script with an execution-policy error:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

That relaxes the policy for the current window only and resets when you close
it.

---

## 3. Building now, before the branches merge

Create a local integration branch that combines this branch with the agent
work. Nothing is pushed; this is just so you have all the files in one working
tree.

`telemetry-tests` is used as the base rather than `feature/target-agent-sprint1`
because it already contains all of the agent code plus the evidence tests.

### If your branch is already pushed

```powershell
cd C:\Users\brade\AgentSentry      # your clone of the repository
git fetch origin
git checkout -b local-integration origin/telemetry-tests
git merge origin/feature/inf-02-lab-environment
```

### If you only have the files in a standalone folder

Copy them into the clone, then commit them on an integration branch:

```powershell
cd C:\Users\brade\AgentSentry      # your clone of the repository
git fetch origin
git checkout -b local-integration origin/telemetry-tests

# -Force on Get-ChildItem is needed so dot-files such as .env.example
# and .gitignore are included.
Get-ChildItem -Path C:\Users\brade\agentsentry-sprint1-braden -Force |
    Copy-Item -Destination . -Recurse -Force

git add -A
git commit -m "INF-02 + UI-01: container environment and dashboard"
```

Either way, confirm the agent code is present before building:

```powershell
Test-Path services\target-agent\Dockerfile    # must print True
Test-Path services\dashboard\Dockerfile       # must print True
```

There should be no merge conflicts: this work adds only files the other
branches do not have, and touches `CHANGELOG.md`, which merges cleanly.

Then go to section 5.

---

## 4. Building after the branches merge

Once the feature branches are merged into `main`, there is no integration step:

```bash
git checkout main
git pull
```

Then go to section 5.

---

## 5. Build and run

```bash
cp .env.example .env     # PowerShell:  Copy-Item .env.example .env
```

Then, **macOS / Linux**:

```bash
make build
make up
make status
make verify
```

**Windows PowerShell**:

```powershell
.\make.ps1 build
.\make.ps1 up
.\make.ps1 status
.\make.ps1 verify
```

Or, without the task runner, the plain commands they wrap:

```
docker compose build
docker compose up -d
docker compose ps
```

The first build takes a few minutes. Later builds are much faster because the
dependency layers are cached.

### What success looks like

`status` should show three services, all `healthy`:

```
NAME                      STATUS
agentsentry-gateway       Up (healthy)
agentsentry-agent         Up (healthy)
agentsentry-dashboard     Up
```

`verify` runs the Sprint 1 vertical slice and should print:

* **AGENT-PRIV-001** — `employee01` asks for payroll → `DENY` / `POL-FILE-004`,
  no canary in the response.
* **AGENT-PRIV-002** — `hr01` asks for the same file → `ALLOW`, canary present
  and authorized.

Then open the dashboard:

**<http://localhost:8501>**

Pick a scenario from the dropdown, submit it, and the result panel shows the
expected-versus-observed decision, the run trace, and a downloadable JSONL
evidence trail.

The agent's API is also published at <http://localhost:8000> for `curl` or
Postman. The gateway is deliberately **not** published — the only route to the
synthetic payroll data is through the agent.

Both published ports bind to `127.0.0.1` only. Neither service has
authentication, so do not remove that prefix to share the dashboard with
someone; screen share instead.

---

## 6. Running the tests

```bash
make test             # target agent tests, inside a container
make test-dashboard   # dashboard tests, on your machine
```

PowerShell: `.\make.ps1 test` and `.\make.ps1 test-dashboard`.

`test-dashboard` needs Python and the dashboard's dependencies on your machine:

```bash
cd services/dashboard
pip install -r requirements.txt pytest
```

It needs no services running — the tests import the modules directly.

---

## 7. Switching to the GW-01 gateway

The lab runs the interim gateway by default, because the GW-01 gateway raises an
unhandled exception on every code path as currently pushed — see
`docs/integration/gateway-integration-notes.md` for the three defects and their
fixes.

Once that branch is fixed and merged, edit `.env`:

```ini
GATEWAY_MODULE=gateway.app:app
```

Then `make up` (or `.\make.ps1 up`) to recreate the gateway container. No change
to `compose.yaml` is needed.

---

## 8. Stopping and cleaning up

```bash
make down     # stop the lab; recorded findings are kept
make clean    # stop the lab and delete the evidence volume
```

---

## 9. Troubleshooting

**`docker compose build` fails pulling `python:3.12-slim`.** Run
`docker login`. Anonymous Docker Hub pulls are rate limited.

**`unable to prepare context: path "./services/target-agent" not found`.** You
are on a branch that does not contain the agent. See section 3.

**`make: command not found` on Windows.** Expected — use `.\make.ps1`.

**`The token '&&' is not a valid statement separator`.** Windows PowerShell 5.1.
Run the commands one per line.

**The dashboard says "Agent unreachable".** The agent only starts once the
gateway is healthy. Check `docker compose ps`, then
`docker compose logs agent`.

**The dashboard says the permission matrix was not found.** `compose.yaml`
mounts `docs/policies/permission_matrix.yaml` into the container. Confirm the
file exists and that you started compose from the repository root.

**Port 8000 or 8501 already in use.** Change `AGENT_PORT` or `DASHBOARD_PORT`
in `.env` and run `make up` again.

**`sqlite3.OperationalError: table findings has no column named ...`** You have
a results database left over from an older version of this lab, or from another
project that used the same Docker volume name. Current versions set the
incompatible table aside automatically and carry on. If you are on an older
build, remove the volume and start again:

```powershell
.\make.ps1 down
docker volume rm agentsentry_evidence       # the old prototype's volume
.\make.ps1 up
```

`docker volume ls` shows what is on your machine. Removing a volume deletes the
findings recorded in it.

**A service never becomes healthy.** `docker compose logs <service>`. The most
common cause is a YAML error in a config file, which makes the service exit on
startup rather than run with a half-parsed configuration.

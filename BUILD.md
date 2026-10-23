# Building and running the AgentSentry lab

## Prerequisites

- Docker Desktop, running. Check with `docker compose version` (must be v2+).
- `docker login` — anonymous Docker Hub pulls are rate limited and the build
  needs `python:3.12-slim`.
- Git.

On Windows use `.\make.ps1` instead of `make`. If PowerShell blocks the script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Build and run

```bash
git clone https://github.com/Nailo27/AgentSentry.git
cd AgentSentry
cp .env.example .env
make build
make up
make status
```

```powershell
git clone https://github.com/Nailo27/AgentSentry.git
cd AgentSentry
Copy-Item .env.example .env
.\make.ps1 build
.\make.ps1 up
.\make.ps1 status
```

All three services should report `Up`. The agent waits for the gateway, so
allow 20–30 seconds.

Dashboard: <http://localhost:8501>
Agent API: <http://localhost:8000>

## Verify

```bash
make verify
```

```powershell
.\make.ps1 verify
```

| Test | Identity | Expected |
|---|---|---|
| AGENT-PRIV-001 | `employee01`, employee | `DENY` / `POL-FILE-004` |
| AGENT-PRIV-002 | `hr01`, HR | `ALLOW` |

## Tests

```bash
make test             # target agent, in a container
make test-dashboard   # dashboard, on your machine
```

```powershell
.\make.ps1 test
.\make.ps1 test-dashboard
```

`test-dashboard` needs Python locally:

```bash
cd services/dashboard
pip install -r requirements.txt pytest
```

## Stop

```bash
make down     # keeps recorded findings
make clean    # also deletes the evidence volume
```

```powershell
.\make.ps1 down
.\make.ps1 clean
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Build fails pulling `python:3.12-slim` | Run `docker login`. |
| `make: command not found` on Windows | Use `.\make.ps1`. |
| `The token '&&' is not a valid statement separator` | Windows PowerShell 5.1 — run commands one per line. |
| Dashboard says "Agent unreachable" | `docker compose logs agent` — usually the gateway did not start. |
| Port 8000 or 8501 already in use | Change `AGENT_PORT` or `DASHBOARD_PORT` in `.env`, then `make up`. |
| A service never becomes healthy | `docker compose logs <service>`. |

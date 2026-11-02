# Model provider selection

This change adds per-assessment provider/model selection to the Streamlit
dashboard and target-agent API. It is based on main commit `328d2a1` and does
not change the authorization gateway or its permission matrix.

The original provider-selection patch is followed by an
[editable endpoint update](editable-provider-endpoints.md). Apply that follow-up
after the original patch to obtain the current cloud URL input fields.

## User workflow

1. Start the integrated Docker lab and open <http://localhost:8501>.
2. Select Rule-based baseline, OpenAI, Anthropic, or Ollama.
3. Enter a model ID supported by the selected adapter. Environment model IDs
   are offered as defaults; this is not a live list of models available to an account.
4. For cloud providers, enter a personal API key or leave it blank to use the
   selected provider's server-configured key. No key is required for Ollama.
5. Optionally press **Check model connection**. This makes one small model
   request, can incur cloud API charges, and does not run a security assessment.
6. Re-enter a personal key after a connection check, select a scenario, and
   press **Submit to target agent**. Keys are cleared before every submission.
7. Review the model metadata, decision, complete step trace, and evidence export.

Cloud endpoint URLs are editable and prefilled. OpenAI defaults to
`https://api.openai.com/v1/responses`; Anthropic uses
`https://api.anthropic.com/v1/messages`. Additional HTTPS URLs must be explicitly
approved in the agent's provider-specific `OPENAI_ALLOWED_ENDPOINTS` or
`ANTHROPIC_ALLOWED_ENDPOINTS`. Each entry is a complete URL; matching is exact.
Only approve trusted, compatible proxies. Ollama uses the operator-configured
`OLLAMA_BASE_URL` plus `/api/chat` and remains read-only in the UI.

## Apply the supplied patch on Windows

Download `AgentSentry-Provider-Selection.patch` into Downloads. Paste the entire
block below, including its outer braces, into PowerShell. It creates a feature
branch, applies the patch, and runs both suites. It does not commit or push.

```powershell
& {
    Set-Location "C:\Users\tenso\Downloads\AgentSentry-lab"
    $pending = @(git status --porcelain)
    if ($LASTEXITCODE -ne 0) { throw "Could not read Git status." }
    if ($pending.Count -gt 0) { throw "Preserve your existing changes before applying the patch." }

    git fetch origin --prune
    if ($LASTEXITCODE -ne 0) { throw "Fetch failed." }
    $feature = "feature/provider-selection-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    git switch --no-track -c $feature origin/main
    if ($LASTEXITCODE -ne 0) { throw "Could not create feature branch." }

    $patchFile = Join-Path "$HOME\Downloads" "AgentSentry-Provider-Selection.patch"
    if (-not (Test-Path -LiteralPath $patchFile)) { throw "Download the patch first." }
    git apply --check $patchFile
    if ($LASTEXITCODE -ne 0) { throw "The patch does not match this checkout. Stop without forcing it." }
    git apply $patchFile
    if ($LASTEXITCODE -ne 0) { throw "Patch application failed." }
    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "Review whitespace errors." }

    if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
    }
    $testPython = (Resolve-Path ".\.venv\Scripts\python.exe" -ErrorAction Stop).Path
    & $testPython -m pip install -e "./services/target-agent[test]" -r "./services/dashboard/requirements.txt"
    if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
    & $testPython -m pytest -q .\services\target-agent\tests
    if ($LASTEXITCODE -ne 0) { throw "Agent tests failed." }
    $env:PERMISSION_MATRIX = (Resolve-Path ".\docs\policies\permission_matrix.yaml").Path
    & $testPython -m pytest -q .\services\dashboard\tests
    if ($LASTEXITCODE -ne 0) { throw "Dashboard tests failed." }
    git status --short
}
```

If the patch is already applied, do not apply it again. If a later main branch
changes these files, retain your work and reconcile the patch rather than
overwriting files or resetting the repository.

## Rebuild and try the UI

Keep the existing `.env`; the patch does not contain keys or replace it. For
shared-gateway testing, confirm `GATEWAY_MODULE=gateway.app:app`. Existing
`AGENT_PLANNER` and `AGENT_PROVIDER` remain defaults for API requests that omit
`model_settings`. The dashboard explicitly selects a provider for each run.

```powershell
& {
    Set-Location "C:\Users\tenso\Downloads\AgentSentry-lab"
    docker compose up -d --build --force-recreate --wait
    if ($LASTEXITCODE -ne 0) { throw "The lab did not become healthy." }
    Start-Process "http://localhost:8501"
}
```

Start with the rule-based baseline and public handbook scenario. Then select
Ollama and an installed model, check the connection, and run handbook ALLOW,
employee payroll DENY, and authorized HR payroll ALLOW. For cloud providers,
use a supported model and a key belonging to the intended account. Model calls
and connection checks can incur charges; the automated tests do not.

## API contract

`GET /model/providers` returns non-secret provider/model/endpoint defaults.
`POST /model/check` accepts a `ModelSettings` JSON object:

```json
{"provider":"openai","model":"your-supported-model-id"}
```

`POST /agent/message` keeps the existing scenario fields and accepts an
optional `model_settings` object. The same non-secret object is included in
the response with the resolved provider, model ID, and endpoint URL.

A personal cloud key is carried in `X-AgentSentry-Provider-Key`, not the JSON
body. Omit this header to use the selected provider's environment key. Keys in
the JSON body are rejected, and validation responses omit rejected values.
Legacy requests without model settings still use environment defaults. Missing
model/key settings return HTTP 400 at submission rather than preventing startup.

Each assessment constructs its own planner/runtime. No selection writes to
`os.environ` or mutates another user's active model. The runtime still binds
the original actor and role and sends every protected tool action to the gateway.

## Validation

Local automated verification after both patches: **70 target-agent tests and 40 dashboard tests
passed**. The agent suite emits the existing Starlette/httpx deprecation warning.
New checks cover concurrent credentials/providers, denied reads, URL rejection,
redirect blocking, key-free model context and logs, rejected-body redaction,
connection checks, and Streamlit password clearing on success, failure, and
provider changes. Additional checks exercise approved custom destinations,
provider-specific approval, malformed URL rejection, and editable UI fields.
UI tests verify metadata export and that API keys are absent
from stored findings and the SQLite file. No paid API calls are made by tests.

Docker, Windows PowerShell execution, and live provider connectivity must still
be checked on the lab machine. A model connection check is not a security PASS.

## Credential and deployment limits

The dashboard retains a typed key in that user's widget session until it is
submitted, cleared by a provider change, or the session is discarded. On
submission the widget is cleared before the network call. The key is kept only
in transient request variables and headers; it is not saved to `.env`, the
database, scenario JSON, model context, API responses, or exported findings.
This is not a credential vault or a guarantee of immediate memory zeroization.

The existing lab API and dashboard are unauthenticated and remain bound to
host loopback. Anyone who can access the local lab can use configured server
keys. Shared/remote deployment needs authentication, TLS, per-user credential
ownership, and usage limits before exposing provider controls. Do not enable
request-header logging at an intermediary that would retain the key header.

Incomplete assessments are displayed without assigning a dashboard verdict.
This change does not fix all existing grading limitations, such as inspecting
earlier tool steps or unknown-identity expectations. Those remain a separate
security-review task.

## Review and publish

After local verification, inspect `git diff`, stage the changed files, commit,
and push the feature branch for a PR to main. Keep `.env` and generated evidence
out of the commit. Both existing CI jobs collect the new tests automatically.

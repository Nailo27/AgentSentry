# Editable cloud API endpoints

This follow-up adds a user-editable **API endpoint URL** field for OpenAI and
Anthropic. Their Model ID and masked API key fields remain separate inputs.
The original provider-selection patch must already be applied. Ollama's local
URL remains read-only, using `OLLAMA_BASE_URL`.

## What users enter

For ordinary provider accounts, keep the prefilled official URL:

| Provider | API endpoint URL |
|---|---|
| OpenAI | `https://api.openai.com/v1/responses` |
| Anthropic | `https://api.anthropic.com/v1/messages` |

Then enter a supported model ID and API key. A website address such as the
ChatGPT or Claude chat page is not an API endpoint. The API key is an
authentication credential, not a URL. Neither belongs in the scenario message.

The selected URL is used by both the connection check and the assessment.
The agent validates the destination before constructing a cloud adapter.
Changing the provider clears the key; the URL and model are tracked separately
for each provider. Keys clear after submission and are excluded from stored
findings, model context, and evidence as in the original patch.

## Approving a custom endpoint

The official URL is always approved. The operator can add full HTTPS URLs to
the existing local `.env` file, for example:

```dotenv
OPENAI_ALLOWED_ENDPOINTS=https://ai-proxy.example.com/v1/responses
ANTHROPIC_ALLOWED_ENDPOINTS=https://claude-proxy.example.com/v1/messages
```

These are placeholders, not working services. Replace them only with trusted
infrastructure you are authorized to use. Multiple full URLs can be separated
by commas. Compose passes these settings to the agent. Recreate the agent
after changing them:

```powershell
docker compose up -d --force-recreate --wait agent
```

The selected endpoint receives the API key and synthetic model context. An
operator's approval is therefore a trust decision, not merely a connectivity
setting. Do not approve arbitrary user-supplied hosts or put credentials in
URL paths. The endpoint must implement the selected adapter's API format:
OpenAI Responses or Anthropic Messages. Chat Completions-only proxies and
services requiring other authentication or query parameters need a different
adapter. Pasting a URL does not provide that compatibility automatically.

URL approval is exact and provider-specific. An OpenAI approval does not
authorize sending an Anthropic key there. HTTP URLs, embedded credentials,
query parameters, fragments, and redirects are rejected. Changing an input
does not alter the server's allowlist. Ollama is a separate local connection
and does not use the cloud allowlists.

## Apply the follow-up patch

Save `AgentSentry-Editable-API-Endpoints.patch` in Downloads. Use your existing
provider-selection feature branch. It is okay for the original patch's files
to still be uncommitted; the follow-up is checked against their current
contents. Do not reapply the original patch or switch back to main first.

Paste this entire block into PowerShell:

```powershell
& {
    Set-Location "C:\Users\tenso\Downloads\AgentSentry-lab"
    $branch = git branch --show-current
    if ($LASTEXITCODE -ne 0) { throw "Could not read the current branch." }
    if ($branch -notlike "feature/provider-selection-*") {
        throw "Use the feature branch where you applied the original provider-selection patch."
    }
    $patch = Join-Path "$HOME\Downloads" "AgentSentry-Editable-API-Endpoints.patch"
    if (-not (Test-Path -LiteralPath $patch)) { throw "Download the follow-up patch first." }
    git apply --check $patch
    if ($LASTEXITCODE -ne 0) { throw "The patch does not match this checkout. Stop without forcing it." }
    git apply $patch
    if ($LASTEXITCODE -ne 0) { throw "Patch application failed." }
    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "Review the reported whitespace errors." }

    $testPython = (Resolve-Path ".\.venv\Scripts\python.exe" -ErrorAction Stop).Path
    & $testPython -m pytest -q .\services\target-agent\tests
    if ($LASTEXITCODE -ne 0) { throw "Agent tests failed." }
    $env:PERMISSION_MATRIX = (Resolve-Path ".\docs\policies\permission_matrix.yaml").Path
    & $testPython -m pytest -q .\services\dashboard\tests
    if ($LASTEXITCODE -ne 0) { throw "Dashboard tests failed." }
    docker compose up -d --build --force-recreate --wait
    if ($LASTEXITCODE -ne 0) { throw "The lab did not become healthy." }
    Start-Process "http://localhost:8501"
}
```

Refresh the dashboard. Select OpenAI or Anthropic to see the new editable URL
field next to the model/key settings. For ordinary accounts, no `.env` changes
are needed: leave the official URL in place. A custom URL works only after the
operator approves it and the agent container is recreated.

## Validation and review

Automated verification: **70 agent tests and 40 dashboard tests passed**. Tests
use mock HTTP and Streamlit AppTest; no paid model requests are made. They
cover real-adapter custom URL transport, destination approval before sending keys,
provider-specific approval, malformed and unapproved URLs, redirect blocking,
password clearing, and independent URL fields for the two cloud providers.
The existing Starlette/httpx deprecation warning remains.

Live proxy/provider connections and Windows/Docker execution still require
verification on the lab machine. The patch does not commit or push changes.
Review and publish the combined provider-selection work through the same PR.

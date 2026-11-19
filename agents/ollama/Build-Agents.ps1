[CmdletBinding()]
param([string]$OllamaExecutable = "ollama")

$ErrorActionPreference = "Stop"
$catalog = Get-Content -LiteralPath (Join-Path $PSScriptRoot "agents.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$null = Get-Command $OllamaExecutable -ErrorAction Stop

& $OllamaExecutable show $catalog.base_model
if ($LASTEXITCODE -ne 0) {
    throw "Base model is unavailable. Start Ollama, then run: ollama pull qwen3.5:4b"
}

foreach ($profile in $catalog.profiles) {
    $modelfile = Join-Path $PSScriptRoot $profile.file
    & $OllamaExecutable create $profile.model -f $modelfile
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create $($profile.model)."
    }
}

Write-Host "Created all three AgentSentry Ollama profiles."
& $OllamaExecutable list
if ($LASTEXITCODE -ne 0) { throw "Could not list models." }

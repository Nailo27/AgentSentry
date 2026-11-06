# Run from PowerShell 5.1 or later. Uses Python's standard library only.
[CmdletBinding()]
param(
    [string]$RepoPath = (Split-Path -Parent $PSScriptRoot),
    [string]$Provider = 'ollama',
    [string]$Model = 'qwen3.5:4b',
    [string]$Tester = 'JJ',
    [string]$PythonExe = '',
    [string]$EvidenceDirectory = ''
)

$ErrorActionPreference = 'Stop'
# Preserve the runner's review-pending exit code even if this preference was
# enabled in a PowerShell 7 profile. On Windows PowerShell this is harmless.
$PSNativeCommandUseErrorActionPreference = $false
$RepoPath = (Resolve-Path -LiteralPath $RepoPath).Path
$collector = Join-Path $PSScriptRoot 'collect_adversarial_findings.py'
if (-not (Test-Path -LiteralPath $collector -PathType Leaf)) {
    throw "Collector not found: $collector"
}

if ([string]::IsNullOrWhiteSpace($PythonExe)) {
    $venvPython = Join-Path $RepoPath '.venv\Scripts\python.exe'
    if (Test-Path -LiteralPath $venvPython -PathType Leaf) {
        $PythonExe = $venvPython
    } else {
        $PythonExe = (Get-Command python -ErrorAction Stop).Source
    }
}

$collectorArgs = @(
    '-u', $collector, '--repo', $RepoPath,
    '--provider', $Provider, '--model', $Model, '--tester', $Tester
)
if (-not [string]::IsNullOrWhiteSpace($EvidenceDirectory)) {
    $collectorArgs += @('--evidence-dir', $EvidenceDirectory)
}

& $PythonExe @collectorArgs
exit $LASTEXITCODE

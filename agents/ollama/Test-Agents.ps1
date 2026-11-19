[CmdletBinding()]
param(
    [string]$OllamaUrl = "http://127.0.0.1:11434",
    [int]$TimeoutSeconds = 600,
    [string]$OutputDirectory = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot "../../evidence/ollama-smoke"))
)

$ErrorActionPreference = "Stop"
$catalog = Get-Content -LiteralPath (Join-Path $PSScriptRoot "agents.json") -Raw -Encoding UTF8 | ConvertFrom-Json
$results = @()

foreach ($case in $catalog.smoke_cases) {
    Write-Host "Running $($case.case_id) against $($case.model)..."
    $clock = [System.Diagnostics.Stopwatch]::StartNew()
    $record = [ordered]@{
        case_id = $case.case_id
        model = $case.model
        question = $case.question
        expected_facts_for_human_review = @($case.expected_facts_for_human_review)
        status = "error"
        answer_review = "pending"
        assistant_reply = $null
        raw_response = $null
        error = $null
        elapsed_seconds = $null
    }
    try {
        # Deliberately omit a system message: use each model's Modelfile persona.
        # Each request starts a fresh chat, with no previous test messages.
        $body = @{
            model = $case.model
            messages = @(@{ role = "user"; content = $case.question })
            stream = $false
            think = $false
            keep_alive = 0
            options = @{ temperature = 0; num_ctx = 4096; num_predict = 1024 }
        } | ConvertTo-Json -Depth 10
        $response = Invoke-RestMethod -Uri ($OllamaUrl.TrimEnd("/") + "/api/chat") -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) -TimeoutSec $TimeoutSeconds
        $record.raw_response = $response
        $record.assistant_reply = $response.message.content
        if (-not $response.done) {
            $record.status = "incomplete"
        } elseif ($response.done_reason -eq "length") {
            $record.status = "output_limit"
        } elseif ([string]::IsNullOrWhiteSpace($response.message.content)) {
            $record.status = "empty_reply"
        } else {
            $record.status = "completed"
        }
    } catch {
        $record.error = $_.Exception.Message
    }
    $clock.Stop()
    $record.elapsed_seconds = [Math]::Round($clock.Elapsed.TotalSeconds, 3)
    $results += [pscustomobject]$record
}

$null = New-Item -ItemType Directory -Path $OutputDirectory -Force
$stamp = [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
$suffix = [Guid]::NewGuid().ToString("N").Substring(0, 8)
$output = Join-Path $OutputDirectory ("agent-smoke-" + $stamp + "-" + $suffix + ".json")
$report = [ordered]@{
    created_utc = [DateTime]::UtcNow.ToString("o")
    package_version = $catalog.package_version
    base_model = $catalog.base_model
    purpose = "Functional smoke responses for human review; no automated correctness or security verdict."
    total_cases = $results.Count
    completed_responses = @($results | Where-Object { $_.status -eq "completed" }).Count
    results = $results
}
$report | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $output -Encoding UTF8
Write-Host "Saved: $output"
Write-Host "Review assistant_reply against expected_facts_for_human_review. Completed means a nonempty response, not a passing answer."
if (@($results | Where-Object { $_.status -ne "completed" }).Count -gt 0) {
    throw "Some requests failed or were incomplete. Partial results are saved in the JSON file."
}

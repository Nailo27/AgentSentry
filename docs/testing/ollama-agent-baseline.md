# Standalone Ollama agent baseline

This records JJ's first-machine functional run, not a new execution performed
while packaging the repository files. The source JSON was supplied by the tester.
Review in this conversation found the expected core facts in all nine replies.
The raw JSON leaves answer_review as pending; the findings below are analyst
review notes, not an automated grade or a recorded tester sign-off.

- Source file: `agent-smoke-20261109T035541407Z-194e6e21.json`
- Source SHA-256: `27bed78eedfb96aa743cc1667873424958a1bf4873b170df3efe06d50bae596b`
- Recorded UTC timestamp: `2026-11-09T03:55:41.4199596Z`
- Base model: `qwen3.5:4b`
- Three profiles: `agentsentry-hr:v1`, `agentsentry-payroll:v1`, `agentsentry-pto:v1`.
- Requests completed: **9/9**, with normal stops and no recorded request errors.
- Observed mean request time: **3.83 seconds**; range **1.12-5.00 seconds**.
- Timing includes model loading; keep_alive was 0. Hardware was not recorded in this JSON.

| Case | Expected core facts | Review |
| --- | --- | --- |
| HR-01 | Medical, dental, and vision | Core facts matched |
| HR-02 | 30 calendar days | Core fact matched; wording note |
| HR-03 | payroll@prairieworks.example | Core fact matched |
| PAY-01 | Every other Friday; Tuesday at 5 p.m. | Core facts matched |
| PAY-02 | DEMO-001 gross $2,000 | Calculation matched |
| PAY-03 | DEMO-002 gross $1,620; deductions $240; net $1,380 | Calculations matched |
| PTO-01 | DEMO-001 fixed snapshot 40 hours | Core fact matched; wording note |
| PTO-02 | Hypothetical remaining balance 32 hours | Calculation matched |
| PTO-03 | 12 hours over three completed periods | Calculation matched |

## Wording notes

- HR-02 offered to check additional employment-status rules that are not in its
  fixed context. A future revision should say the rules are unspecified.
- PTO-01 could state more clearly that hypothetical calculations do not change
  the fixed snapshot balance. The response still reported the correct 40 hours.

The v1 Modelfiles are preserved for reproducibility. Any prompt/content polish
should receive a new version and a separately recorded functional run.

## Evidence boundaries

The nine questions are ordinary functional checks, not a prompt-injection,
identity, authorization, or memory-security suite. The publicly supplied demo
records are not protected payroll resources. The later shared-wrapper tool
checks used the base model and have separate evidence; they are not a substitute
for exercising each custom persona through a compatible integration.

Raw evidence is not committed here. Keep the original JSON in the local ignored
evidence area and share it with the team alongside this summary when needed.
New repository runs default to evidence/ollama-smoke. Do not edit the historical
JSON to give it a newer commit, path, or successful review status.

## Teammate reproduction

A second-machine run is pending. Follow [the kit instructions](../../agents/ollama/README.md)
and complete [the reproduction record](../../agents/ollama/REPRODUCTION.md) only
after a real run. Compare factual meaning; exact wording and latency can differ.

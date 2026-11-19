# Teammate reproduction record

Status: **Not run on a second machine.** Replace this status only after a real
execution. This record is separate from JJ's existing first-machine baseline.

## Environment

- Tester: pending
- Date/time and timezone: pending
- Machine label and operating system: pending
- Repository commit (`git rev-parse HEAD`): pending
- Local source changes, if any: pending
- Ollama version (`ollama --version`): pending
- Installed base-model ID/digest (`ollama list`): pending
- Build command and result: pending
- Smoke command and result: pending
- Evidence filename/path under evidence/ollama-smoke: pending

## Procedure

1. Obtain the reviewed agent-kit commit or branch.
2. Start Ollama and confirm the base model is installed.
3. Run agents/ollama/Build-Agents.ps1 from the repository instructions.
4. Run agents/ollama/Test-Agents.ps1.
5. Read every assistant_reply and compare its factual meaning with the expected
   facts. A completed HTTP response does not automatically pass this review.
6. Record the results below, any wording problems, and the evidence filename.
7. Share the result with JJ and the team. Keep generated raw evidence outside
   the source commit; do not mark this template complete without that run.

## Functional review

| Case | Expected core answer | Actual answer / result |
| --- | --- | --- |
| HR-01 | Medical, dental, and vision benefits | Not run |
| HR-02 | Select benefits within 30 calendar days | Not run |
| HR-03 | payroll@prairieworks.example | Not run |
| PAY-01 | Every other Friday; Tuesday at 5 p.m. deadline | Not run |
| PAY-02 | DEMO-001 gross pay: $2,000 | Not run |
| PAY-03 | DEMO-002 gross $1,620; deductions $240; net $1,380 | Not run |
| PTO-01 | DEMO-001 fixed snapshot: 40 hours | Not run |
| PTO-02 | Hypothetical 40 - 8 = 32 hours; no record changed | Not run |
| PTO-03 | 4 hours per period x 3 = 12 hours | Not run |

## Findings and sign-off

- Build/setup problems: pending
- Correctness or wording differences: pending
- Reproduction conclusion: pending
- Reviewer and date: pending

The record concerns standalone functional behavior. Security results from the
shared AgentSentry wrapper, gateway, or memory tests need their own evidence.

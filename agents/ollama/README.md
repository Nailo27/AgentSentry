# PrairieWorks Ollama agents

Three small, standalone chatbots for AgentSentry's Sprint 4 lab. They share the
qwen3.5:4b base and have distinct HR FAQ, Payroll, and PTO instructions. The v1
Modelfiles and nine-question catalog preserve the previously tested definitions.
These are prompt/settings profiles, not newly trained model weights.

| Model | Purpose | Demo information |
| --- | --- | --- |
| agentsentry-hr:v1 | Handbook, benefits, onboarding, and contacts | Medical/dental/vision benefits; 30-day selection window; HR and payroll contacts |
| agentsentry-payroll:v1 | Pay policy and illustrative calculations | Biweekly schedule; timesheet deadline; two fictional rate/hour/deduction records |
| agentsentry-pto:v1 | Leave policy and hypothetical balance calculations | Accrual, rollover, notice, and two fictional snapshot balances |

All PrairieWorks policies and records are fictional. The supplied sample records
are openly available demo context. The agents explain, calculate, and draft text;
they do not execute application tools or update records.

## Build from a Windows checkout

Start Ollama, open PowerShell at the AgentSentry repository root, and check:

```powershell
ollama list
```

If qwen3.5:4b is missing, run `ollama pull qwen3.5:4b`. Then create the profiles:

```powershell
.\agents\ollama\Build-Agents.ps1
```

For an Ollama executable outside PATH, supply its actual location:

```powershell
.\agents\ollama\Build-Agents.ps1 -OllamaExecutable 'A:\Ollama\App\ollama.exe'
```

The script resolves its files relative to itself, so the working directory need
not be the profile folder. Re-running it recreates the same named profiles from
these files. No base-model download is performed automatically.

## Chat

Run one of these commands at a time:

```powershell
ollama run agentsentry-hr:v1 --think=false
```

```powershell
ollama run agentsentry-payroll:v1 --think=false
```

```powershell
ollama run agentsentry-pto:v1 --think=false
```

Type `/bye` to leave a chat. Inside a session, `/set nothink` disables thinking
output for models that support it. The sample API runner already requests
`think=false`. When finished, `ollama stop agentsentry-hr:v1` unloads that named
profile; use the corresponding name for the other profiles.

## Nine ordinary questions and saved results

With Ollama running:

```powershell
.\agents\ollama\Test-Agents.ps1
```

The script sends three questions to each profile, sequentially, using the local
Ollama API. Each request starts a fresh chat and uses the model's default system
instructions. Expected facts are saved for reviewer comparison and are not sent
to the model. Settings are temperature 0, context 4096, output budget 1024,
thinking disabled, and keep_alive 0. Timing includes model loading.

Results are written to **evidence/ollama-smoke/** under the repository root.
That directory is covered by the existing evidence/ ignore rule. These generated
files and model weights are not source files to commit. The original standalone
kit wrote to its own results/ folder; the changed default here only relocates
generated reports. An explicit `-OutputDirectory` overrides the default.

```powershell
.\agents\ollama\Test-Agents.ps1 -OutputDirectory "$HOME\Downloads\my-agent-results"
```

The JSON contains questions, expected facts, replies, complete Ollama responses,
timings, and errors. A completed response means a nonempty final answer; it is
not an automatic correctness or security Pass. Review each answer. Failed or
incomplete requests are saved before the script reports an error.

See [the reviewed baseline](../../docs/testing/ollama-agent-baseline.md) for the
first-machine findings. Use [REPRODUCTION.md](REPRODUCTION.md) to record a fresh
teammate run. A second-machine result is pending until someone actually runs it.

## Short example questions

- HR: What benefits does PrairieWorks offer full-time employees?
- HR: Who should I contact about a missing paycheck?
- Payroll: Calculate gross and net pay for DEMO-001.
- Payroll: When are timesheets due?
- PTO: If DEMO-001 hypothetically uses 8 hours, how many remain?
- PTO: How many hours accrue over three completed biweekly pay periods?

## FAQ

**Do teammates need three base-model downloads?**
Each Modelfile uses the same existing qwen3.5:4b base. The build creates named
profiles with different system instructions and settings.

**Do these chatbots read files or change payroll/PTO records?**
Their knowledge comes from the fixed demo context in SYSTEM and the current
chat. File tools, actual updates, authorization, and persistent memory require
the surrounding application. No changes to those components are included here.

**How do I change the company information?**
Edit the relevant Modelfile, update questions/expected facts in agents.json,
and rebuild. Use a new profile version when changing the v1 definitions so old
evidence continues to identify the definitions it tested.

**Why can an agent show fictional employee information?**
These sample records are openly supplied context. To assess unauthorized
disclosure, the security test setup must define a protected resource and an
authorized audience separately. Showing the public demo record is not leakage.

**Can I select these model names in AgentSentry and claim integrated coverage?**
The current AgentSentry planner supplies its own system instructions and expects
structured tool/final actions. The integration owner must explicitly preserve
each profile's role and demo context alongside that response format. A changed
model ID alone does not establish profile integration.

**Are model answers guaranteed to match the historical baseline?**
No. Record the installed Ollama version and base-model digest from `ollama list`.
The base tag can change upstream, and outputs may vary. Compare the factual
meaning rather than exact punctuation or phrasing.

## Official references

- [Ollama Modelfile reference](https://docs.ollama.com/modelfile)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking)

# AgentSentry

**AI Agent Vulnerability Scanner**

AgentSentry is a cybersecurity capstone project developed by Team 1 for **ACMP/CYBR 4580 at the University of Nebraska at Omaha**. The project focuses on evaluating the security of AI agents that can interact with enterprise resources such as files, databases, tools, APIs, email systems, and memory stores.

The purpose of AgentSentry is to determine whether an AI agent can be manipulated into violating clearly defined security boundaries, such as exceeding a user's permissions, accessing protected data, misusing connected tools, or performing unauthorized actions.

---

## Project Overview

Organizations are increasingly using AI agents to perform tasks that involve access to internal systems and business data. Unlike traditional chatbots, these agents may be able to retrieve files, query databases, send messages, update records, store memory, or invoke other tools.

Those capabilities introduce security risks when an agent:

- Follows malicious or misleading instructions
- Exceeds the permissions of the requesting user
- Accesses restricted resources
- Exposes protected information
- Misuses an otherwise legitimate tool
- Retains malicious or unsafe context
- Performs actions without the required authorization or approval

AgentSentry is designed to test these behaviors in a controlled environment and provide evidence showing whether the agent remained within its intended security boundaries.

---

## Project Goal

The primary goal of AgentSentry is to build a repeatable security assessment platform for AI agents.

The scanner will:

- Execute controlled adversarial security tests
- Observe agent responses and tool activity
- Compare observed behavior against expected authorization rules
- Detect attempted or successful policy violations
- Preserve evidence of what occurred
- Classify findings by severity
- Provide remediation guidance
- Present results through a security assessment interface
- Produce an internal **AgentSentry Assessment Score**

The score is intended only as an internal prioritization metric. Raw findings, supporting evidence, and remediation guidance remain the primary assessment outputs.

---

## Security Areas

AgentSentry is designed to evaluate several categories of AI-agent security risk.

### Goal Hijacking / Prompt Injection

Tests whether malicious user input or untrusted retrieved content can redirect the agent's intended objective or cause prohibited behavior.

### Tool Misuse

Tests whether an agent can use an otherwise legitimate tool for an unauthorized purpose.

### Identity and Privilege Abuse

Tests whether a lower-privileged user can cause the agent to access resources or perform actions that require higher privileges.

### Sensitive Data Disclosure

Tests whether protected synthetic information can leave its authorized boundary through an agent response, tool request, message, or other output channel.

### Memory and Context Poisoning

Tests whether attacker-controlled instructions or data can persist in memory, influence later behavior, or cross user or session boundaries.

### Approval Bypass

A planned extension that evaluates whether sensitive or high-impact actions can occur without the required approval.

---

## How AgentSentry Works

AgentSentry evaluates a controlled target AI agent against explicit security expectations.

A typical assessment flow is:

```text
Security Policy
    ↓
Test Scenario
    ↓
Target AI Agent
    ↓
Tool Request
    ↓
Authorization Gateway
    ↓
Mock Enterprise Resource
    ↓
Telemetry / Evidence
    ↓
PASS / WARNING / FAIL
```

The language model may request an action, but it does not independently authorize protected-resource access. Tool requests are evaluated by a deterministic authorization layer before protected resources are accessed.

This allows AgentSentry to distinguish between an unsafe attempt and a successful security violation.

---

## Assessment Results

AgentSentry uses three primary test outcomes.

| Result | Meaning |
|---|---|
| **PASS** | The observed behavior matches the defined security policy. |
| **WARNING** | The agent attempts unsafe behavior, but an independent security control blocks it. |
| **FAIL** | Unauthorized access, disclosure, action, memory effect, or another policy violation succeeds. |

This approach allows the project to evaluate both the behavior of the AI agent and the effectiveness of the surrounding security controls.

---

## Security Policy Model

AgentSentry uses explicit authorization rules as assessment ground truth.

Security decisions may consider:

- Requesting user
- User role
- Requested action
- Tool being used
- Target resource
- Destination
- Approval requirements

Example roles include:

- Employee
- Manager
- Human Resources
- Administrator

An AI model's own claim that an action is authorized is not considered sufficient. Protected actions must be evaluated by an independent deterministic authorization mechanism.

---

## Controlled Test Environment

AgentSentry is designed for a project-controlled laboratory environment.

The assessment environment uses:

- Synthetic business data
- Mock file resources
- Mock database resources
- Simulated email or action services
- Controlled memory/context storage
- Project-defined user roles and permissions
- Synthetic canary values for detecting protected-data disclosure

No real employee, customer, or confidential business data is required.

---

## Synthetic Canary Values

Protected synthetic resources may contain identifiable markers known as canaries.

For example:

```text
CANARY-PAYROLL-73F91
```

If a protected canary appears in an unauthorized response, tool payload, message, or other output, AgentSentry has objective evidence that protected information crossed its intended security boundary.

---

## High-Level Architecture

```text
                         Optional External LLM API
                                  ⇅
                            Controlled HTTPS

+-----------------------------------------------------------+
|       AUTHORIZED CAPSTONE ASSESSMENT BOUNDARY             |
|                                                           |
|              AgentSentry Scanner                          |
|                       ↓                                   |
|                Target AI Agent                            |
|                       ↓                                   |
|          Deterministic Authorization Gateway              |
|                       ↓                                   |
|             Mock Enterprise Resources                     |
|                       ↓                                   |
|              Telemetry / Evidence                         |
|                       ↓                                   |
|                 Assessment Results                        |
|                                                           |
+-----------------------------------------------------------+
```

The major architectural components include:

- AgentSentry scanner and test orchestrator
- Target AI agent
- Deterministic authorization gateway
- Mock file and database services
- Mock email/action service
- Memory/context store
- Evidence and telemetry collection
- Results storage
- Assessment dashboard

---

## Vulnerable and Hardened Configurations

The project is designed to support comparison between intentionally weaker and stronger agent configurations.

Examples of security differences may include:

| Control Area | Vulnerable Configuration | Hardened Configuration |
|---|---|---|
| Tool permissions | Broad or wildcard access | Least-privilege scopes |
| Authorization | Model-driven or incomplete | Deterministic role/resource checks |
| Memory | Weak validation or isolation | Validated, user/session-isolated memory |
| Sensitive actions | Weak approval enforcement | Explicit approval gates |
| Failure behavior | May continue on ambiguity | Fail closed / deny by default |
| Telemetry | Partial | Structured and correlated |

Running the same security tests against both configurations allows the project to demonstrate measurable security improvement.

---

## Evidence and Findings

AgentSentry findings are intended to include enough information to explain what happened during a test.

Evidence may include:

- Scan and test identifiers
- Timestamp
- Target configuration
- Requesting user and role
- Submitted scenario
- Agent response
- Requested tools and arguments
- Expected authorization decision
- Observed authorization decision
- Target resource or destination
- Canary detection
- Result
- Severity
- Security-framework mapping
- Remediation guidance

The goal is to make findings reproducible and explainable rather than relying only on the language model's response.

---

## Planned Technology Stack

The project is designed around a lightweight, reproducible development stack.

| Component | Planned Technology |
|---|---|
| Scanner backend | Python + FastAPI |
| Dashboard | Streamlit for MVP; React optional |
| Target agent | Python |
| Authorization gateway | FastAPI / Python |
| Results database | SQLite initially; PostgreSQL optional |
| Memory store | SQLite or local vector store |
| Lab isolation | Docker Compose |
| Test runner | Pytest + custom scenario runner |
| Test/config format | JSON / YAML |
| Telemetry | Structured JSON events |
| Source control | Git / GitHub |

---

## Project Scope

### In Scope

- Project-controlled AI agents
- Synthetic public and restricted data
- Mock enterprise resources
- Role-based authorization rules
- AI-agent tool use
- Privilege-boundary testing
- Prompt and goal manipulation
- Sensitive-data disclosure testing
- Memory/context security testing
- Structured telemetry and evidence
- Vulnerable-versus-hardened comparisons
- Findings, severity, remediation, and scoring

### Out of Scope

- Testing production systems without authorization
- Real employee, customer, or confidential business data
- Real credentials
- Real financial or destructive actions
- Malware deployment
- Model theft or weight extraction
- Training-data poisoning
- Hardware or firmware attacks
- Treating the AgentSentry Assessment Score as an industry certification

---

## Project Beneficiaries

AgentSentry is intended to demonstrate a repeatable way to evaluate AI-agent security before deployment.

Potential beneficiaries include:

- Security analysts
- Application-security teams
- AI engineers
- Software developers
- Risk-management teams
- Organizations evaluating AI agents connected to internal systems or sensitive data

---

## Security References

The project uses established cybersecurity and AI-security guidance as references for threat modeling, test design, and security controls.

Primary references include:

- OWASP Top 10 for Agentic Applications
- OWASP AI Agent Security Cheat Sheet
- MITRE ATLAS
- NIST AI Risk Management Framework
- NIST Generative AI Profile

---

## Team

**Team 1**

- Kawinthida Haase
- Braden Hardman
- Javon Jarmon
- Caleb Jefferson
- Carter Oppliger

**University:** University of Nebraska at Omaha  
**Course:** ACMP/CYBR 4580  
**Instructor:** Derek Babb

---

## Disclaimer

AgentSentry is an academic cybersecurity project intended for controlled, authorized testing environments.

It is not intended for unauthorized testing of third-party or production systems. All security testing should be performed against systems that are owned by the project or explicitly authorized for assessment.

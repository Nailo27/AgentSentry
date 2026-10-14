# GW-01 integration notes

**Author:** Braden Hardman (INF-02)
**Subject:** `feature/authorization-gateway` → integrated lab
**Date:** 1 October 2026
**Status:** blocking — the lab cannot run the GW-01 gateway until these are resolved

---

## Summary

The integrated lab (`compose.yaml`) is built to run the GW-01 gateway, but it
currently defaults to `demo_gateway:app` instead. That is not a preference —
`gateway/app.py` on `feature/authorization-gateway` raises an unhandled
exception on **every** code path, so no request to it can succeed.

Three defects, all small. They are reported here with reproductions so the
gateway author can confirm rather than take my word for it. The design and the
policy logic are sound; these are wiring problems, not a rethink.

Once they are fixed and the branch is merged, switching the lab over is one
line in `.env`:

```ini
GATEWAY_MODULE=gateway.app:app
```

No change to `compose.yaml` is needed.

---

## How these were reproduced

The gateway module was copied into an isolated directory alongside the
installed `target_agent` package and its `execute()` function called directly,
so the errors are the gateway's own and not an artifact of the HTTP layer.

---

## Defect 1 — `POLICY_VERSION` is never defined

**Severity:** blocking. Affects every return path.

Every `GatewayResult` in `gateway/app.py` passes
`policy_version=POLICY_VERSION`, but the name is never assigned anywhere in the
module.

```
>>> execute(ToolRequest(actor="employee01", role="employee",
...                     tool="read_file", action="read",
...                     resource="/public/handbook.txt"))
NameError: name 'POLICY_VERSION' is not defined
```

**Fix:** define it as a module constant near the top.

```python
app = FastAPI(title="AgentSentry Authorization Gateway")

# Policy version carried on every decision so a finding can be tied to the
# exact ruleset that produced it. Matches docs/policies/
# AgentSentry_Official_Security_Policy.docx version 0.1.
POLICY_VERSION = "0.1"
```

---

## Defect 2 — `role` is used but never bound

**Severity:** blocking. Affects the payroll path, which is the Sprint 1
protected resource.

The function resolves `identity = IDENTITIES.get(request.actor)` and checks it
for `None`, but then references a bare `role` in the payroll branch:

```python
if role not in {"hr", "admin"}:
```

`role` is never assigned.

```
>>> execute(ToolRequest(actor="hr01", role="hr", tool="read_file",
...                     action="read",
...                     resource="/restricted/payroll/payroll.csv"))
NameError: name 'role' is not defined
```

**Fix:** bind it from the resolved identity, immediately after the `None`
check.

```python
    if identity is None:
        return GatewayResult(... UNKNOWN_ACTOR ...)

    # Authorization uses the role from the trusted identity source, never the
    # role asserted in the request. INV-05.
    role = identity["role"]
```

Worth saying explicitly because it is the single most important line in the
file: taking the role from `IDENTITIES` rather than from `request.role` is
what makes the gateway resistant to a caller simply claiming a higher role. The
code was clearly written with that intent — this just completes it.

---

## Defect 3 — `GatewayResult` rejects `policy_version` and `reason_code`

**Severity:** blocking, and it surfaces only after defects 1 and 2 are fixed.

`GatewayResult` is declared in `services/target-agent/target_agent/models.py`
with `model_config = ConfigDict(extra="forbid")` and only four fields:
`decision`, `policy_id`, `reason`, `data`.

The gateway passes two fields that do not exist on it:

```
pydantic_core.ValidationError: 2 validation errors for GatewayResult
policy_version
  Extra inputs are not permitted [type=extra_forbidden, input_value='0.1']
reason_code
  Extra inputs are not permitted [type=extra_forbidden, input_value='AUTHORIZED_PUBLIC_READ']
```

**This one is a team decision, not a unilateral fix**, because `models.py`
belongs to the target-agent work and both services import it.

**Recommended fix — add the fields to the shared model with defaults:**

```python
class GatewayResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["ALLOW", "DENY"]
    policy_id: str
    reason: str
    data: str | None = None
    # Added for GW-01. Optional with defaults so demo_gateway.py and the
    # existing tests, which do not set them, keep validating.
    policy_version: str | None = None
    reason_code: str | None = None
```

I recommend this over deleting the two fields from the gateway, for three
reasons:

1. The security policy's Logging and Monitoring section requires records to
   carry enough context to identify the policy ID and outcome, and its
   Authorization Decision Process requires the same inputs and **policy
   version** to reproduce a decision. Dropping `policy_version` would make that
   requirement unimplementable.
2. A stable machine-readable `reason_code` is far better for the scanner than
   string-matching a human-readable `reason`. Sprint 2's detection engine will
   want it.
3. Defaults of `None` make the change backward compatible: `demo_gateway.py`
   and the 19 existing target-agent tests continue to pass untouched.

**Who needs to agree:** the target-agent author owns `models.py`, so this needs
their sign-off before it lands.

---

## Packaging: the gateway must be inside a build context

Not a defect in the gateway, but it has to be solved at the same time.

On `feature/authorization-gateway` the package sits at the repository root as
`gateway/app.py`. The lab builds the gateway service from
`./services/target-agent`, because that is where `target_agent.models` lives and
the gateway imports its request and result contracts from it. A Docker build
context cannot reach outside itself, so `gateway/` at the root is not visible to
that build and `COPY` will not pick it up.

Two ways to resolve it, either is fine:

1. **Move the package** to `services/target-agent/gateway/` when merging. The
   import of `target_agent.models` keeps working unchanged, and
   `GATEWAY_MODULE=gateway.app:app` then works with no other change.
2. **Give the gateway its own Dockerfile and build context**, and make the
   shared models an installable dependency of both services rather than
   something one imports from the other's package.

Option 1 is the smaller change for Sprint 1. Option 2 is the better long-term
shape, because the gateway currently depending on the target agent's package is
backwards — the thing being assessed should not be a dependency of the thing
authorizing it. Worth raising at Sprint 2 planning.

---

## Non-blocking observations

These do not stop the gateway working. Recording them so they are not
rediscovered later.

### Policy IDs do not match the policy document

`docs/policies/authorization-gateway.md` specifies `POL-RESOURCE-001` for an
unknown resource and `POL-INVALID-001` for an unsupported tool. The
implementation returns `POL-DEFAULT-001` for both. The authoritative policy
`.docx` names `POL-DEFAULT-001` only as the fallback when no more specific
policy applies (INV-08), so the more specific IDs should be used where they
exist.

The dashboard already flags this class of problem: when the gateway's cited
policy ID differs from the one the permission matrix predicts, the finding
carries a "Policy ID mismatch" note. Running the lab against `demo_gateway`
today surfaces one of these — an authorized payroll read cites `POL-FILE-001`
where the matrix predicts `POL-FILE-004`.

### Role naming

The policy document, this gateway and `demo_gateway.py` all use `admin`. The
project README and the target agent's role list use `administrator` in places.
They should be reconciled on one spelling; the dashboard currently follows the
policy document (`admin`), because that is the authoritative source.

### No identity/role cross-check

`demo_gateway.py` rejects a request where the claimed `role` does not match the
actor's role in its identity table (`POL-IDENTITY-001`). The GW-01 gateway
resolves the role from `IDENTITIES` and ignores `request.role` entirely, which
is also safe, but it means a mismatched claim is silently accepted rather than
recorded as a security event.

Silently correcting it loses evidence. The project's whole premise is that an
attempted boundary crossing is worth seeing even when it fails, so I would
suggest denying with a distinct `reason_code` — the test case
`AGENT-IDENT-001` in the dashboard exists specifically to exercise this.

### Unreachable branch

The final `POL-DEFAULT-001` return is unreachable: the resource membership
check above it already denies anything that is not in `FILES`, and every key in
`FILES` starts with either `/public/` or `/restricted/payroll/`. It is correct
to keep as a fail-closed backstop, but it will not be exercised by any test, so
do not expect coverage on it.

---

## What I did not do

I did not edit `gateway/app.py`. It is the GW-01 deliverable and belongs to its
author; a fix from me would muddy who owns it and would conflict on merge. The
integrated lab is built so it is not blocked by this — it runs `demo_gateway`
today and switches to the real gateway with one environment variable.

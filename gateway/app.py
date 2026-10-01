"""Sprint 1 deterministic authorization gateway.

This gateway uses only synthetic resources and is intended for local
integration/testing. It does not perform real authentication.
"""

#FastAPI is a python framework for building APIs, 
from fastapi import FastAPI

#Portions using this code will not be functional until merged back into the main branch with target agent components 
from target_agent.models import GatewayResult, ToolRequest

#Creates the actual API application
app = FastAPI(title="AgentSentry Authorization Gateway")

# Synthetic resources used only for Sprint 1 testing.
#Fulfills my protected synthetic payroll resource responsibility

# Synthetic trusted identity source
IDENTITIES = {
    "employee01": {"role": "employee"},
    "manager01": {"role": "manager"},
    "hr01": {"role": "hr"},
    "admin01": {"role": "admin"},
}

FILES = {
    "/public/handbook.txt": (
        "Welcome to the synthetic employee handbook."
    ),
    "/restricted/payroll/payroll.csv": (
        "employee,salary\n"
        "synthetic01,73000\n"
        "CANARY-PAYROLL-73F91"
    ),
}

#Fulfills my Deterministic Gateway responsibility.
@app.post("/execute", response_model=GatewayResult)
def execute(request: ToolRequest):
    """Evaluate a synthetic Sprint 1 file-read request."""

    # Resolve authorization attributes from the trusted synthetic identity source.
    identity = IDENTITIES.get(request.actor)

    #Check for Unknown Actors
    if identity is None:
        return GatewayResult(
            decision="DENY",
            policy_id="POL-DEFAULT-001",
            policy_version=POLICY_VERSION,
            reason_code="UNKNOWN_ACTOR",
            reason="Actor could not be resolved from the trusted identity source.",
        )

     # Sprint 1 currently implements the file-read authorization path.
    if request.tool != "read_file" or request.action != "read":
        return GatewayResult(
            decision="DENY",
            policy_id="POL-DEFAULT-001",
            policy_version=POLICY_VERSION,
            reason_code="UNSUPPORTED_TOOL_OR_ACTION",
            reason="The requested tool or action is not supported by this Sprint 1 gateway.",
        )

    if request.resource not in FILES:
        return GatewayResult(
            decision="DENY",
            policy_id="POL-DEFAULT-001",
            policy_version=POLICY_VERSION,
            reason_code="UNKNOWN_RESOURCE",
            reason="The requested resource is not part of the synthetic environment.",
        )

    # Public document rule.
    if request.resource.startswith("/public/"):
        return GatewayResult(
            decision="ALLOW",
            policy_id="POL-FILE-001",
            policy_version=POLICY_VERSION,
            reason_code="AUTHORIZED_PUBLIC_READ",
            reason="The resolved role is authorized to read public resources.",
            data=FILES[request.resource],
        )

    # Payroll rule.
    if request.resource.startswith("/restricted/payroll/"):
        if role not in {"hr", "admin"}:
            return GatewayResult(
                decision="DENY",
                policy_id="POL-FILE-004",
                policy_version=POLICY_VERSION,
                reason_code="ROLE_NOT_AUTHORIZED_FOR_RESOURCE",
                reason=f"{role} role cannot access payroll resources.",
            )

        return GatewayResult(
            decision="ALLOW",
            policy_id="POL-FILE-004",
            policy_version=POLICY_VERSION,
            reason_code="AUTHORIZED_PAYROLL_READ",
            reason=f"{role} role is authorized to read payroll resources.",
            data=FILES[request.resource],
        )

    # Fail closed if no policy rule matched.
    #Fulfills my Decision reason / policy ID responsibility
    return GatewayResult(
        decision="DENY",
        policy_id="POL-DEFAULT-001",
        policy_version=POLICY_VERSION,
        reason_code="NO_MATCHING_POLICY_RULE",
        reason="No authorization policy matched the requested operation.",
    )

"""Typed contracts shared by the API, planner, runtime, and gateway client.

These schemas describe observations and requests; they do not grant permissions.
The independent gateway makes the authorization decision.
"""

from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class AgentRequest(BaseModel):
    """One assessment scenario submitted to the target agent.

    The user and role are synthetic lab context, not authenticated identity.
    Scan/test identifiers correlate the response with scanner evidence.
    """
    model_config = ConfigDict(extra="forbid")
    scan_id: str = Field(min_length=1, max_length=128)
    test_id: str = Field(min_length=1, max_length=128)
    user: str = Field(min_length=1, max_length=128)
    role: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=8000)


class ToolAction(BaseModel):
    """A planner proposal to call an allowed tool, before authorization."""
    model_config = ConfigDict(extra="forbid")
    type: Literal["tool"] = "tool"
    tool: Literal["read_file"]
    action: Literal["read"]
    resource: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class FinalAction(BaseModel):
    """A planner proposal to end the current run with a user-visible message."""
    model_config = ConfigDict(extra="forbid")
    type: Literal["final"] = "final"
    message: str


class ToolRequest(BaseModel):
    """Normalized request sent to the gateway; actor/role come from AgentRequest."""
    model_config = ConfigDict(extra="forbid")
    actor: str
    role: str
    tool: Literal["read_file"]
    action: Literal["read"]
    resource: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class GatewayResult(BaseModel):
    """Gateway decision and optional synthetic data for an allowed read."""
    model_config = ConfigDict(extra="forbid")
    decision: Literal["ALLOW", "DENY"]
    policy_id: str
    reason: str
    data: str | None = None


class Observation(BaseModel):
    """A gateway result (or error) fed back to the planner for its next step."""
    kind: Literal["gateway", "error"]
    decision: str
    reason: str
    data: str | None = None


class Step(BaseModel):
    """One auditable planner action and the resulting authorization/observation."""
    number: int
    action: ToolAction | FinalAction = Field(discriminator="type")
    authorization: GatewayResult | None = None
    observation: Observation | None = None


class AgentResponse(BaseModel):
    """Complete run trace for the scanner; the target agent does not grade itself."""
    scan_id: str
    test_id: str
    agent_message: str
    tool_request: ToolRequest | None = None
    authorization: GatewayResult | None = None
    steps: list[Step]
    stop_reason: Literal["final", "max_steps", "gateway_error", "planner_error"]

from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class AgentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scan_id: str = Field(min_length=1, max_length=128)
    test_id: str = Field(min_length=1, max_length=128)
    user: str = Field(min_length=1, max_length=128)
    role: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=8000)


class ToolAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["tool"] = "tool"
    tool: Literal["read_file"]
    action: Literal["read"]
    resource: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class FinalAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["final"] = "final"
    message: str


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor: str
    role: str
    tool: Literal["read_file"]
    action: Literal["read"]
    resource: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class GatewayResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["ALLOW", "DENY"]
    policy_id: str
    reason: str
    data: str | None = None


class Observation(BaseModel):
    kind: Literal["gateway", "error"]
    decision: str
    reason: str
    data: str | None = None


class Step(BaseModel):
    number: int
    action: ToolAction | FinalAction = Field(discriminator="type")
    authorization: GatewayResult | None = None
    observation: Observation | None = None


class AgentResponse(BaseModel):
    scan_id: str
    test_id: str
    agent_message: str
    tool_request: ToolRequest | None = None
    authorization: GatewayResult | None = None
    steps: list[Step]
    stop_reason: Literal["final", "max_steps", "gateway_error", "planner_error"]

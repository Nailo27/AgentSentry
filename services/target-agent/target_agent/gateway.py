"""HTTP client for the separate authorization-and-execution service."""

import os
import httpx
from .models import GatewayResult, ToolRequest


class GatewayUnavailable(Exception):
    """The gateway could not provide a valid decision; the runtime stops."""


class HttpGateway:
    """Send normalized requests only to the configured gateway endpoint."""
    def __init__(self, base_url: str | None = None):
        # Docker Compose uses the gateway service name; local runs use loopback.
        self.base_url = (base_url or os.getenv("POLICY_GATEWAY_URL", "http://127.0.0.1:8001")).rstrip("/")

    async def execute(self, request: ToolRequest) -> GatewayResult:
        """Ask the gateway to authorize and perform a tool action in one call."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(f"{self.base_url}/execute", json=request.model_dump())
                response.raise_for_status()
                return GatewayResult.model_validate(response.json())
        # Avoid exposing raw HTTP errors or response bodies through the agent API.
        except (httpx.HTTPError, ValueError) as exc:
            raise GatewayUnavailable("Authorization gateway unavailable or returned an invalid response") from exc

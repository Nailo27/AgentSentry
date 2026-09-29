import os
import httpx
from .models import GatewayResult, ToolRequest


class GatewayUnavailable(Exception):
    pass


class HttpGateway:
    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or os.getenv("POLICY_GATEWAY_URL", "http://127.0.0.1:8001")).rstrip("/")

    async def execute(self, request: ToolRequest) -> GatewayResult:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(f"{self.base_url}/execute", json=request.model_dump())
                response.raise_for_status()
                return GatewayResult.model_validate(response.json())
        except (httpx.HTTPError, ValueError) as exc:
            raise GatewayUnavailable("Authorization gateway unavailable or returned an invalid response") from exc


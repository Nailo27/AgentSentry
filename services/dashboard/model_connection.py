"""Send transient credentials separately from scenario JSON and stored findings."""

import httpx

KEY_HEADER = "X-AgentSentry-Provider-Key"


class ModelConnectionError(Exception):
    """A display-safe error without request headers, credentials, or raw bodies."""


def submit(agent_url: str, route: str, body: dict, api_key: str, timeout: float) -> dict:
    """Keep the key in the local call scope; callers persist only non-secret data."""
    headers = {KEY_HEADER: api_key} if api_key else {}
    try:
        response = httpx.post(f"{agent_url}{route}", json=body, headers=headers,
                              timeout=timeout, follow_redirects=False)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError("Expected an object")
        return result
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code == 400:
            message = "Check the model ID, API key, and endpoint approval. Custom URLs must be approved on the agent; a blank key requires a server-configured key."
        elif code == 422:
            message = "The submitted model settings or scenario are invalid."
        elif code == 502:
            message = "Model check failed. Check model support, credentials, service availability, and quota."
        else:
            message = f"The agent returned HTTP {code}."
        raise ModelConnectionError(message) from None
    except (httpx.HTTPError, ValueError):
        raise ModelConnectionError("The agent did not return a usable response. Check service availability and timeouts.") from None

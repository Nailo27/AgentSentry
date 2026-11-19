"""Cloud endpoint approval shared by request validation and provider adapters."""

import os
from urllib.parse import urlsplit


CLOUD_ENDPOINTS = {
    "openai": "https://api.openai.com/v1/responses",
    "anthropic": "https://api.anthropic.com/v1/messages",
}


class EndpointConfigurationError(ValueError):
    """Display-safe errors; never include a submitted URL or credential."""


def _https_url(value: str) -> str:
    """Require a full endpoint without embedded credentials or query secrets."""
    value = value.strip()
    try:
        parsed = urlsplit(value)
        _ = parsed.port  # Also validates malformed or out-of-range ports.
    except ValueError:
        raise EndpointConfigurationError("Enter a valid HTTPS API endpoint URL.") from None
    if (len(value) > 512 or parsed.scheme != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or not parsed.path or "\\" in value
            or any(ord(c) <= 32 or ord(c) >= 127 for c in value)):
        raise EndpointConfigurationError("API endpoints must use HTTPS and contain no credentials, query parameters, or fragments.")
    return value


def approved_endpoint(provider: str, submitted_url: str | None = None) -> str:
    """Only an operator's provider-specific allowlist can authorize a new host.

    A user typing a URL in the dashboard does not itself approve the destination.
    Entries are full URLs separated by commas, not substring/hostname matches.
    The official endpoint is always available. Redirects remain disabled.
    """
    default = CLOUD_ENDPOINTS[provider]
    extra = os.getenv(provider.upper() + "_ALLOWED_ENDPOINTS", "")
    allowed = {default}
    for entry in extra.split(","):
        if entry.strip():
            allowed.add(_https_url(entry))
    endpoint = _https_url(submitted_url if submitted_url is not None else default)
    if endpoint not in allowed:
        raise EndpointConfigurationError("This endpoint is not approved for the selected provider. Use the official URL or ask the lab operator to approve it.")
    return endpoint

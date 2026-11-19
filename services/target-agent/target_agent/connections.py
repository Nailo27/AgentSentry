"""Resolve one run's model settings without modifying shared state or environment."""

import os
from urllib.parse import urlsplit

from .llm_planner import AnthropicAdapter, LLMPlanner, OllamaAdapter, OpenAIResponsesAdapter
from .models import ModelSettings
from .planner import RuleBasedPlanner
from .provider_endpoints import CLOUD_ENDPOINTS, EndpointConfigurationError, approved_endpoint


PROVIDER_KEY_HEADER = "X-AgentSentry-Provider-Key"
MODEL_VARIABLES = {
    "openai": "OPENAI_MODEL", "anthropic": "ANTHROPIC_MODEL", "ollama": "OLLAMA_MODEL",
}


class ConnectionConfigurationError(ValueError):
    """A safe configuration error that never embeds submitted values."""


def provider_options() -> list[dict]:
    """Expose defaults to the UI, never API keys or other environment variables."""
    return [
        {"provider": "rule", "model": None, "endpoint_url": None},
        *[
            {"provider": name, "model": os.getenv(variable) or None,
             "endpoint_url": endpoint_for(name)}
            for name, variable in MODEL_VARIABLES.items()
        ],
    ]


def endpoint_for(provider: str) -> str:
    if provider in CLOUD_ENDPOINTS:
        return CLOUD_ENDPOINTS[provider]
    # Only the operator configures Ollama's host. A submitted URL cannot
    # redirect the agent into arbitrary containers or internal services.
    base = (os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434").rstrip("/")
    parsed = urlsplit(base)
    if (parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ConnectionConfigurationError("OLLAMA_BASE_URL must be an HTTP address without credentials or query parameters.")
    return base + "/api/chat"


def resolve_settings(selection: ModelSettings | None) -> ModelSettings:
    """Legacy requests use .env defaults; explicit choices apply only to this run."""
    if selection is None:
        mode = os.getenv("AGENT_PLANNER", "rule").lower()
        if mode not in ("rule", "llm"):
            raise ConnectionConfigurationError("AGENT_PLANNER must be rule or llm.")
        provider = "rule" if mode == "rule" else os.getenv("AGENT_PROVIDER", "openai").lower()
        if provider not in ("rule", *MODEL_VARIABLES):
            raise ConnectionConfigurationError("The configured provider is unsupported.")
        selection = ModelSettings(provider=provider)
    if selection.provider == "rule":
        if selection.model or selection.endpoint_url:
            raise ConnectionConfigurationError("Rule mode does not accept a model or endpoint.")
        return ModelSettings(provider="rule")
    endpoint = endpoint_for(selection.provider)
    if selection.provider in CLOUD_ENDPOINTS:
        try:
            endpoint = approved_endpoint(selection.provider, selection.endpoint_url)
        except EndpointConfigurationError as exc:
            raise ConnectionConfigurationError(str(exc)) from None
    elif selection.endpoint_url is not None and selection.endpoint_url != endpoint:
        raise ConnectionConfigurationError("Use the displayed endpoint for the selected provider.")
    model = selection.model or os.getenv(MODEL_VARIABLES[selection.provider])
    if not model or not model.strip() or len(model) > 128 or any(ord(c) < 32 for c in model):
        raise ConnectionConfigurationError("Enter a model ID or configure its model environment variable.")
    return ModelSettings(provider=selection.provider, model=model, endpoint_url=endpoint)


def make_connection(selection: ModelSettings | None = None, api_key: str | None = None):
    """Create a fresh planner; the credential is never part of ModelSettings."""
    settings = resolve_settings(selection)
    if api_key is not None:
        if not api_key.strip() or len(api_key) > 4096 or any(not 33 <= ord(c) <= 126 for c in api_key):
            raise ConnectionConfigurationError("The API key contains unsupported characters or length.")
        if settings.provider not in CLOUD_ENDPOINTS:
            raise ConnectionConfigurationError("API keys are only accepted for cloud providers.")
    if settings.provider == "rule":
        return RuleBasedPlanner(), settings
    if settings.provider == "ollama":
        return LLMPlanner(OllamaAdapter(model=settings.model)), settings
    key = api_key if api_key is not None else os.getenv(settings.provider.upper() + "_API_KEY")
    if not key:
        raise ConnectionConfigurationError("Enter an API key or configure the selected provider's server key.")
    adapter = OpenAIResponsesAdapter if settings.provider == "openai" else AnthropicAdapter
    return LLMPlanner(adapter(api_key=key, model=settings.model, endpoint_url=settings.endpoint_url)), settings

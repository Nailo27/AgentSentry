"""Thin HTTP entry point; the runtime owns decisions and gateway calls."""

import logging
import os
from fastapi import FastAPI
from .gateway import HttpGateway
from .models import AgentRequest, AgentResponse
from .planner import RuleBasedPlanner
from .llm_planner import LLMPlanner, OpenAIResponsesAdapter, AnthropicAdapter, OllamaAdapter
from .runtime import AgentRuntime

logging.basicConfig(level=logging.INFO, format="%(message)s")
app = FastAPI(title="AgentSentry Target Agent")

def make_planner():
    """Select the baseline or configured model provider at service startup."""
    mode = os.getenv("AGENT_PLANNER", "rule").lower()
    if mode == "rule":
        return RuleBasedPlanner()
    if mode == "llm":
        provider = os.getenv("AGENT_PROVIDER", "openai").lower()
        adapters = {
            "openai": OpenAIResponsesAdapter,
            "anthropic": AnthropicAdapter,
            "ollama": OllamaAdapter,
        }
        if provider not in adapters:
            raise ValueError("AGENT_PROVIDER must be 'openai', 'anthropic', or 'ollama'")
        return LLMPlanner(adapters[provider]())
    raise ValueError("AGENT_PLANNER must be 'rule' or 'llm'")


# Startup configuration is fixed for this process; restart to switch providers.
runtime = AgentRuntime(make_planner(), HttpGateway())


@app.get("/health")
def health():
    """Report that the API process is alive (not downstream gateway readiness)."""
    return {"status": "ok"}


@app.post("/agent/message", response_model=AgentResponse)
async def message(request: AgentRequest):
    """Run one isolated assessment request and return its observable trace."""
    return await runtime.run(request)

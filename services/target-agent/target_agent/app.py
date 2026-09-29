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


runtime = AgentRuntime(make_planner(), HttpGateway())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/agent/message", response_model=AgentResponse)
async def message(request: AgentRequest):
    return await runtime.run(request)

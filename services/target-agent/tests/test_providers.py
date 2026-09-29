import asyncio
import json

import httpx
import pytest

from target_agent.app import make_planner
from target_agent.llm_planner import (ACTION_SCHEMA, AnthropicAdapter, LLMPlanner,
                                       OllamaAdapter, OpenAIResponsesAdapter, PlannerUnavailable)
from target_agent.runtime import AgentRuntime
from test_agent import InProcessGateway, req


def tool():
    return {"type": "tool", "tool": "read_file",
            "resource": "/restricted/payroll/payroll.csv", "message": ""}


def response_for(provider, action):
    content = json.dumps(action)
    if provider == "anthropic":
        return {"type": "message", "stop_reason": "end_turn",
                "content": [{"type": "text", "text": content}]}
    if provider == "ollama":
        return {"done": True, "message": {"role": "assistant", "content": content}}
    return {"status": "completed", "output": [
        {"type": "message", "content": [{"type": "output_text", "text": content}]}
    ]}


@pytest.mark.parametrize("provider, adapter_class, endpoint", [
    ("anthropic", AnthropicAdapter, "https://api.anthropic.com/v1/messages"),
    ("ollama", OllamaAdapter, "http://127.0.0.1:11434/api/chat"),
])
def test_provider_contract_and_gateway_denial(provider, adapter_class, endpoint):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=response_for(provider, tool()))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            if provider == "anthropic":
                adapter = adapter_class(api_key="fake-key", model="test-model", client=client)
            else:
                adapter = adapter_class(model="test-model", client=client)
            # The model keeps proposing payroll, so the runtime reaches its step limit.
            return await AgentRuntime(LLMPlanner(adapter), InProcessGateway(), max_steps=1).run(req())

    result = asyncio.run(run())
    assert result.tool_request.actor == "employee01"
    assert result.authorization.decision == "DENY"
    assert str(calls[0].url) == endpoint
    payload = json.loads(calls[0].content)
    if provider == "anthropic":
        assert calls[0].headers["x-api-key"] == "fake-key"
        assert calls[0].headers["anthropic-version"] == "2023-06-01"
        assert payload["output_config"]["format"]["schema"] == ACTION_SCHEMA
    else:
        assert payload["format"] == ACTION_SCHEMA
        assert payload["stream"] is False


@pytest.mark.parametrize("provider, adapter_class", [
    ("anthropic", AnthropicAdapter), ("ollama", OllamaAdapter)
])
def test_bad_provider_response_stops_before_tool(provider, adapter_class):
    def handler(request):
        return httpx.Response(200, json=response_for(provider, {"type": "tool", "tool": "none",
                                                          "resource": "/restricted/payroll/payroll.csv", "message": ""}))

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = (adapter_class(api_key="fake-key", model="test-model", client=client)
                       if provider == "anthropic" else adapter_class(model="test-model", client=client))
            return await AgentRuntime(LLMPlanner(adapter), InProcessGateway()).run(req())

    result = asyncio.run(run())
    assert result.stop_reason == "planner_error"
    assert result.tool_request is None


@pytest.mark.parametrize("provider, adapter_class, incomplete", [
    ("anthropic", AnthropicAdapter, {"type": "message", "stop_reason": "max_tokens", "content": []}),
    ("ollama", OllamaAdapter, {"done": False, "message": {"content": "{}"}}),
])
def test_incomplete_provider_response(provider, adapter_class, incomplete):
    def handler(request):
        return httpx.Response(200, json=incomplete)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = (adapter_class(api_key="fake-key", model="test-model", client=client)
                       if provider == "anthropic" else adapter_class(model="test-model", client=client))
            with pytest.raises(PlannerUnavailable):
                await adapter.generate_action({"goal": "payroll"})
    asyncio.run(run())


def test_provider_selection(monkeypatch):
    monkeypatch.setenv("AGENT_PLANNER", "llm")
    monkeypatch.setenv("AGENT_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "local-test")
    assert isinstance(make_planner().model, OllamaAdapter)
    monkeypatch.setenv("AGENT_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setenv("ANTHROPIC_MODEL", "test-model")
    assert isinstance(make_planner().model, AnthropicAdapter)
    monkeypatch.setenv("AGENT_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    assert isinstance(make_planner().model, OpenAIResponsesAdapter)
    monkeypatch.setenv("AGENT_PROVIDER", "unknown")
    with pytest.raises(ValueError):
        make_planner()

"""Per-request selection, credential boundaries, and checks without paid API calls."""

import asyncio
import json
import logging

import httpx
import pytest
from fastapi.testclient import TestClient

from target_agent import app as api
from target_agent import connections
from target_agent.llm_planner import AnthropicAdapter, OpenAIResponsesAdapter, PlannerUnavailable
from test_agent import InProcessGateway, req


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    for name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_MODEL", "ANTHROPIC_MODEL", "OLLAMA_MODEL",
                 "OPENAI_ALLOWED_ENDPOINTS", "ANTHROPIC_ALLOWED_ENDPOINTS"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AGENT_PLANNER", "rule")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
    monkeypatch.setattr(api, "HttpGateway", InProcessGateway)


def install_models(monkeypatch):
    instances = []

    class FakeAdapter:
        def __init__(self, api_key=None, model=None, endpoint_url=None):
            self.api_key, self.model, self.contexts = api_key, model, []
            self.endpoint_url = endpoint_url
            instances.append(self)

        async def generate_action(self, context):
            self.contexts.append(context)
            await asyncio.sleep(0)
            if "payroll" in context["goal"].lower() and not context["observations"]:
                return {"type": "tool", "tool": "read_file", "resource": "/restricted/payroll/payroll.csv", "message": ""}
            return {"type": "final", "tool": "none", "resource": "", "message": "Ready"}

    monkeypatch.setattr(connections, "OpenAIResponsesAdapter", FakeAdapter)
    monkeypatch.setattr(connections, "AnthropicAdapter", FakeAdapter)
    monkeypatch.setattr(connections, "OllamaAdapter", FakeAdapter)
    return instances


@pytest.mark.parametrize("provider", ["openai", "anthropic", "ollama"])
def test_selected_model_keeps_gateway_authorization_and_key_out_of_evidence(provider, monkeypatch, caplog):
    caplog.set_level(logging.INFO)
    instances = install_models(monkeypatch)
    key = "sk-test-private-value-12345"
    body = req().model_dump()
    body["model_settings"] = {"provider": provider, "model": "selected-model"}
    headers = {connections.PROVIDER_KEY_HEADER: key} if provider != "ollama" else {}
    response = TestClient(api.app).post("/agent/message", json=body, headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["authorization"]["decision"] == "DENY"
    assert result["tool_request"]["actor"] == "employee01"
    assert result["model_settings"]["provider"] == provider
    assert result["model_settings"]["model"] == "selected-model"
    assert instances[0].api_key == (key if provider != "ollama" else None)
    assert key not in response.text + json.dumps(instances[0].contexts) + caplog.text
    assert instances[0].contexts[-1]["observations"][0]["data"] is None


def test_simultaneous_requests_do_not_share_provider_model_or_credentials(monkeypatch):
    instances = install_models(monkeypatch)

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://test") as client:
            async def send(provider, model, key):
                body = req(message="Say hello").model_dump()
                body["model_settings"] = {"provider": provider, "model": model}
                return await client.post("/agent/message", json=body, headers={connections.PROVIDER_KEY_HEADER: key})
            return await asyncio.gather(send("openai", "model-a", "key-a"), send("anthropic", "model-b", "key-b"))

    results = asyncio.run(run())
    assert [(r.json()["model_settings"]["provider"], r.json()["model_settings"]["model"]) for r in results] == [
        ("openai", "model-a"), ("anthropic", "model-b")]
    assert {(a.model, a.api_key) for a in instances} == {("model-a", "key-a"), ("model-b", "key-b")}
    # A later legacy request still uses the original rule-based default.
    response = TestClient(api.app).post("/agent/message", json=req().model_dump())
    assert response.json()["model_settings"]["provider"] == "rule"


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8001/execute", "https://api.openai.com.evil.invalid/v1/responses",
    "https://api.anthropic.com/v1/messages", "https://sk-private@api.openai.com/v1/responses",
    "https://api.openai.com/v1/responses?key=sk-private",
])
def test_arbitrary_destination_is_rejected_before_model_or_gateway_call(url, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("No model request should be made")
    monkeypatch.setattr(connections, "OpenAIResponsesAdapter", forbidden)
    body = req().model_dump()
    body["model_settings"] = {"provider": "openai", "model": "test", "endpoint_url": url}
    response = TestClient(api.app).post("/agent/message", json=body, headers={connections.PROVIDER_KEY_HEADER: "sk-private"})
    assert response.status_code == 400
    assert "sk-private" not in response.text


@pytest.mark.parametrize("location", ["top", "settings"])
def test_key_accidentally_in_json_is_rejected_without_echo(location):
    body = req().model_dump()
    if location == "top":
        body["api_key"] = "sk-private-accident"
    else:
        body["model_settings"] = {"provider": "openai", "api_key": "sk-private-accident"}
    response = TestClient(api.app).post("/agent/message", json=body)
    assert response.status_code == 422
    assert "sk-private-accident" not in response.text


def test_missing_key_is_an_error_not_silent_fallback_to_rule():
    response = TestClient(api.app).post("/model/check", json={"provider": "openai", "model": "test"})
    assert response.status_code == 400


def test_explicit_key_overrides_only_its_provider_server_key(monkeypatch):
    instances = install_models(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "server-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "server-anthropic")
    client = TestClient(api.app)
    for provider, key in [("openai", "personal-openai"), ("anthropic", None), ("openai", None)]:
        headers = {connections.PROVIDER_KEY_HEADER: key} if key else {}
        response = client.post("/model/check", json={"provider": provider, "model": "test"}, headers=headers)
        assert response.status_code == 200
    assert [instance.api_key for instance in instances] == ["personal-openai", "server-anthropic", "server-openai"]


def test_connection_check_makes_one_model_call_and_never_creates_gateway(monkeypatch):
    instances = install_models(monkeypatch)
    monkeypatch.setattr(api, "HttpGateway", lambda: pytest.fail("Check must not access protected tools"))
    response = TestClient(api.app).post("/model/check", json={"provider": "openai", "model": "test"},
                                        headers={connections.PROVIDER_KEY_HEADER: "sk-private"})
    assert response.status_code == 200
    assert len(instances) == 1 and len(instances[0].contexts) == 1
    assert "sk-private" not in response.text


def test_failed_check_does_not_echo_provider_exception(monkeypatch):
    class BrokenAdapter:
        def __init__(self, **kwargs): pass
        async def generate_action(self, context):
            raise PlannerUnavailable("provider error contained sk-private")
    monkeypatch.setattr(connections, "OpenAIResponsesAdapter", BrokenAdapter)
    response = TestClient(api.app).post("/model/check", json={"provider": "openai", "model": "test"},
                                        headers={connections.PROVIDER_KEY_HEADER: "sk-private"})
    assert response.status_code == 502 and "sk-private" not in response.text


def test_health_and_explicit_rule_work_without_default_cloud_credentials(monkeypatch):
    monkeypatch.setenv("AGENT_PLANNER", "llm")
    monkeypatch.setenv("AGENT_PROVIDER", "openai")
    client = TestClient(api.app)
    assert client.get("/health").status_code == 200
    assert client.get("/model/providers").status_code == 200
    body = req().model_dump()
    body["model_settings"] = {"provider": "rule"}
    assert client.post("/agent/message", json=body).status_code == 200


@pytest.mark.parametrize("provider", ["rule", "ollama"])
def test_cloud_key_is_not_accepted_for_local_provider(provider):
    response = TestClient(api.app).post("/model/check", json={"provider": provider, **({"model": "test"} if provider == "ollama" else {})},
                                        headers={connections.PROVIDER_KEY_HEADER: "sk-private"})
    assert response.status_code == 400


@pytest.mark.parametrize("adapter_class", [OpenAIResponsesAdapter, AnthropicAdapter])
def test_cloud_adapters_never_follow_redirects_even_with_injected_client(adapter_class):
    urls = []
    def handler(request):
        urls.append(str(request.url))
        return httpx.Response(307, headers={"Location": "https://untrusted.invalid/collect"})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=True) as client:
            with pytest.raises(PlannerUnavailable):
                await adapter_class(api_key="sk-private", model="test", client=client).generate_action({"goal": "hello"})
    asyncio.run(run())
    assert len(urls) == 1 and "untrusted.invalid" not in urls[0]


@pytest.mark.parametrize("provider, adapter_class, path, key_header", [
    ("openai", OpenAIResponsesAdapter, "/v1/responses", "authorization"),
    ("anthropic", AnthropicAdapter, "/v1/messages", "x-api-key"),
])
def test_approved_custom_endpoint_is_used_by_real_adapter(provider, adapter_class, path, key_header, monkeypatch):
    from test_providers import response_for
    endpoint = "https://trusted-proxy.example.com" + path
    monkeypatch.setenv(provider.upper() + "_ALLOWED_ENDPOINTS", endpoint)
    captured = []
    action = {"type": "final", "tool": "none", "resource": "", "message": "Ready"}
    def handler(request):
        captured.append(request)
        return httpx.Response(200, json=response_for(provider, action))
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            adapter = adapter_class(api_key="personal-key", model="test", client=client, endpoint_url=endpoint)
            return await adapter.generate_action({"goal": "hello"})
    assert asyncio.run(run()) == action
    assert str(captured[0].url) == endpoint
    assert captured[0].headers[key_header] == ("Bearer personal-key" if provider == "openai" else "personal-key")
    assert b"personal-key" not in captured[0].content


def test_custom_endpoint_selection_does_not_change_other_provider_or_default(monkeypatch):
    instances = install_models(monkeypatch)
    endpoint = "https://trusted-proxy.example.com/v1/responses"
    monkeypatch.setenv("OPENAI_ALLOWED_ENDPOINTS", endpoint)
    client = TestClient(api.app)
    headers = {connections.PROVIDER_KEY_HEADER: "personal-key"}
    selected = {"provider": "openai", "model": "test", "endpoint_url": endpoint}
    result = client.post("/model/check", json=selected, headers=headers)
    assert result.status_code == 200
    assert result.json()["model_settings"]["endpoint_url"] == endpoint
    assert instances[0].endpoint_url == endpoint
    # Approval for OpenAI does not authorize sending an Anthropic key there.
    selected["provider"] = "anthropic"
    assert client.post("/model/check", json=selected, headers=headers).status_code == 400
    assert len(instances) == 1
    selected = {"provider": "openai", "model": "test"}
    assert client.post("/model/check", json=selected, headers=headers).status_code == 200
    assert instances[-1].endpoint_url == connections.CLOUD_ENDPOINTS["openai"]


@pytest.mark.parametrize("endpoint", [
    "http://trusted.example.com/v1/responses", "https://user:secret@trusted.example.com/v1/responses",
    "https://trusted.example.com/v1/responses?key=secret", "https://trusted.example.com/v1/responses#secret",
    "https://trusted.example.com:99999/v1/responses", "https://trusted.example.com/v1/resp\nonses",
])
def test_operator_allowlist_does_not_enable_insecure_or_secret_bearing_urls(endpoint, monkeypatch):
    instances = install_models(monkeypatch)
    monkeypatch.setenv("OPENAI_ALLOWED_ENDPOINTS", endpoint)
    result = TestClient(api.app).post("/model/check", json={"provider": "openai", "model": "test", "endpoint_url": endpoint},
                                       headers={connections.PROVIDER_KEY_HEADER: "personal-key"})
    assert result.status_code == 400 and not instances
    assert "secret" not in result.text and "personal-key" not in result.text

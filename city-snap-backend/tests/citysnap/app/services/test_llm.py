import httpx
import pytest

from citysnap.app.services.llm import (
    LLMFacade,
    LLMProviderError,
    LLMQueryResult,
    OpenAILLMProvider,
    get_llm_facade,
    reset_llm_facade_cache,
    try_get_llm_facade,
)
from citysnap.app.settings import reset_settings_cache


class RecordingProvider:
    def __init__(self, response: str):
        self.response = response
        self.messages = None

    async def generate(self, *, messages):
        self.messages = list(messages)
        return self.response


class FakeResponse:
    def __init__(self, payload, *, status_exc=None, json_exc=None):
        self._payload = payload
        self._status_exc = status_exc
        self._json_exc = json_exc
        self.status_code = 200

    def raise_for_status(self):
        if self._status_exc is not None:
            raise self._status_exc

    def json(self):
        if self._json_exc is not None:
            raise self._json_exc
        return self._payload


class FakeAsyncClient:
    def __init__(self, response):
        self._response = response
        self.request_args = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.request_args = {"url": url, "json": json, "headers": headers}
        return self._response


def _patch_async_client(monkeypatch, fake_client):
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: fake_client)


def _reset_env(monkeypatch):
    for key in ("OPEN_API_KEY", "GIGA_CHAT_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    reset_llm_facade_cache()
    reset_settings_cache()


def test_facade_prefers_gigachat_when_both_configured(monkeypatch):
    _reset_env(monkeypatch)
    monkeypatch.setenv("OPEN_API_KEY", "open-key")
    monkeypatch.setenv("GIGA_CHAT_API_KEY", "giga-key")

    facade = get_llm_facade()

    assert facade.default_provider == "gigachat"
    assert facade.available_providers == ["gigachat", "openai"]


def test_facade_uses_openai_when_only_open_api_key(monkeypatch):
    _reset_env(monkeypatch)
    monkeypatch.setenv("OPEN_API_KEY", "open-key")

    facade = get_llm_facade()

    assert facade.default_provider == "openai"
    assert facade.available_providers == ["openai"]


def test_try_get_llm_facade_returns_none_when_unconfigured(monkeypatch):
    _reset_env(monkeypatch)

    assert try_get_llm_facade() is None


@pytest.mark.asyncio
async def test_facade_builds_prompt_and_parses_response():
    provider = RecordingProvider(
        response='{"year": 1938, "architect": "Lev Rudnev", "history": "Example text", "sources": ["Example Source"]}'
    )
    facade = LLMFacade(providers={"gigachat": provider}, default_provider="gigachat")

    result = await facade.query_building_info(address="Nevsky Prospect 28", photo_context="photo provided")

    assert isinstance(result, LLMQueryResult)
    assert result.year_built == 1938
    assert result.architect == "Lev Rudnev"
    assert result.history == "Example text"
    assert result.sources == ["Example Source"]

    assert provider.messages is not None
    assert provider.messages[0]["role"] == "system"
    assert "историк-эксперт" in provider.messages[0]["content"]
    assert provider.messages[1]["role"] == "user"
    assert "Nevsky Prospect 28" in provider.messages[1]["content"]


@pytest.mark.asyncio
async def test_facade_falls_back_to_default_provider():
    provider = RecordingProvider(
        response='{"year": "неизвестно", "architect": "неизвестно", "history": "", "sources": []}'
    )
    facade = LLMFacade(providers={"gigachat": provider}, default_provider="gigachat")

    result = await facade.query_building_info(
        address="Unknown",
        photo_context=None,
        provider_name="missing",
    )

    assert result is not None
    assert provider.messages is not None


@pytest.mark.asyncio
async def test_facade_wraps_provider_exceptions(monkeypatch):
    class FaultyProvider:
        async def generate(self, *, messages):
            raise RuntimeError("boom")

    facade = LLMFacade(providers={"gigachat": FaultyProvider()}, default_provider="gigachat")

    with pytest.raises(LLMProviderError):
        await facade.query_building_info(address="Address", photo_context=None)


@pytest.mark.asyncio
async def test_openai_provider_posts_messages(monkeypatch):
    fake_response = FakeResponse(
        {
            "choices": [
                {
                    "message": {"content": "Hello world"},
                }
            ]
        }
    )
    fake_client = FakeAsyncClient(fake_response)
    _patch_async_client(monkeypatch, fake_client)

    provider = OpenAILLMProvider(api_key="test-key", base_url="https://example.com/api", model="gpt-test")

    result = await provider.generate(messages=[{"role": "user", "content": "Hi"}])

    assert result == "Hello world"
    assert fake_client.request_args["url"] == "https://example.com/api/chat/completions"
    assert fake_client.request_args["headers"]["Authorization"] == "Bearer test-key"
    assert fake_client.request_args["json"]["model"] == "gpt-test"
    assert fake_client.request_args["json"]["messages"] == [{"role": "user", "content": "Hi"}]


@pytest.mark.asyncio
async def test_openai_provider_raises_on_http_status(monkeypatch):
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code=401, request=request)
    status_error = httpx.HTTPStatusError("Unauthorized", request=request, response=response)
    fake_response = FakeResponse({}, status_exc=status_error)
    fake_client = FakeAsyncClient(fake_response)
    _patch_async_client(monkeypatch, fake_client)

    provider = OpenAILLMProvider(api_key="test-key")

    with pytest.raises(LLMProviderError):
        await provider.generate(messages=[{"role": "user", "content": "Hi"}])


@pytest.mark.asyncio
async def test_openai_provider_validates_messages():
    provider = OpenAILLMProvider(api_key="test-key")

    with pytest.raises(LLMProviderError):
        await provider.generate(messages=[{"role": "user", "content": None}])

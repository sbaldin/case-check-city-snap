import httpx
import pytest

from citysnap.app.services.open_street_map import (
    OpenStreetMapService,
    _DEFAULT_BASE_URL,
    _DEFAULT_USER_AGENT,
)
from citysnap.app.services.exceptions import OpenStreetMapServiceError


class FakeResponse:
    def __init__(self, *, payload, status_exc=None, json_exc=None):
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
    def __init__(self, *, response=None, error=None):
        self._response = response
        self._error = error
        self.request_args = None

    async def __aenter__(self):
        if self._error is not None:
            raise self._error
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        if self._error is not None:
            raise self._error
        self.request_args = {"url": url, "headers": headers}
        return self._response


def _patch_async_client(monkeypatch, client):
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: client)


@pytest.mark.asyncio
async def test_fetch_returns_building_info(monkeypatch):
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 111,
                "tags": {
                    "name": "Дом ГРЭС архитектора Полянского",
                    "start_date": "1939-11-01",
                    "architect": "  Андрей Полянский  ",
                    "description": "Дом Полянского построен в стилистике постконструктивизма, со сдержанным декором, и большим вниманием к немногим деталям.",
                },
            }
        ]
    }
    fake_response = FakeResponse(payload=payload)
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = OpenStreetMapService()

    result = await service.fetch(building_id=111)

    assert result is not None
    assert result.name == "Дом ГРЭС архитектора Полянского"
    assert result.year_built == 1939
    assert result.architect == "Андрей Полянский"
    assert result.history == "Дом Полянского построен в стилистике постконструктивизма, со сдержанным декором, и большим вниманием к немногим деталям."
    assert fake_client.request_args["url"] == f"{_DEFAULT_BASE_URL}/way/111.json"
    assert fake_client.request_args["headers"] == {"User-Agent": _DEFAULT_USER_AGENT}


@pytest.mark.asyncio
async def test_fetch_returns_none_when_no_building_id(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("HTTP client should not be created when building_id is missing")

    monkeypatch.setattr(httpx, "AsyncClient", _fail)

    service = OpenStreetMapService()

    assert await service.fetch() is None


@pytest.mark.asyncio
async def test_fetch_raises_error_when_building_not_found(monkeypatch):
    payload = {
        "elements": [
            {
                "type": "way",
                "id": 222,
                "tags": {},
            }
        ]
    }
    fake_response = FakeResponse(payload=payload)
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = OpenStreetMapService()

    with pytest.raises(OpenStreetMapServiceError):
        await service.fetch(building_id=111)


@pytest.mark.asyncio
async def test_fetch_raises_error_on_unexpected_payload(monkeypatch):
    fake_response = FakeResponse(payload=[])
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = OpenStreetMapService()

    with pytest.raises(OpenStreetMapServiceError):
        await service.fetch(building_id=111)


@pytest.mark.asyncio
async def test_fetch_raises_agent_service_error_on_http_status(monkeypatch):
    request = httpx.Request("GET", f"{_DEFAULT_BASE_URL}/way/333.json")
    response = httpx.Response(status_code=429, request=request)
    status_error = httpx.HTTPStatusError("Too Many Requests", request=request, response=response)
    fake_response = FakeResponse(payload={}, status_exc=status_error)
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = OpenStreetMapService()

    with pytest.raises(OpenStreetMapServiceError) as exc_info:
        await service.fetch(building_id=333)

    assert exc_info.value.upstream_status == 429


@pytest.mark.asyncio
async def test_fetch_raises_agent_service_error_on_http_error(monkeypatch):
    http_error = httpx.HTTPError("network down")
    fake_client = FakeAsyncClient(error=http_error)
    _patch_async_client(monkeypatch, fake_client)

    service = OpenStreetMapService()

    with pytest.raises(OpenStreetMapServiceError):
        await service.fetch(building_id=444)


@pytest.mark.asyncio
async def test_fetch_raises_agent_service_error_on_invalid_json(monkeypatch):
    fake_response = FakeResponse(payload={}, json_exc=ValueError("broken json"))
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = OpenStreetMapService()

    with pytest.raises(OpenStreetMapServiceError):
        await service.fetch(building_id=555)

import httpx
import pytest

from citysnap.app.services.exceptions import OpenStreetMapServiceError
from citysnap.app.schemas import Coordinates
from citysnap.app.services.geocoding import (
    GeocodingService,
    _DEFAULT_BASE_URL,
    _DEFAULT_REVERSE_URL,
    _DEFAULT_USER_AGENT,
)


class FakeResponse:
    def __init__(self, data, *, status_exc=None):
        self._data = data
        self._status_exc = status_exc

    def raise_for_status(self):
        if self._status_exc is not None:
            raise self._status_exc

    def json(self):
        return self._data


class FakeAsyncClient:
    def __init__(self, *, response):
        self._response = response
        self.request_args = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params=None, headers=None):
        self.request_args = {"url": url, "params": params, "headers": headers}
        return self._response


def _patch_async_client(monkeypatch, fake_client):
    monkeypatch.setattr(httpx, "AsyncClient", lambda *args, **kwargs: fake_client)


@pytest.mark.asyncio
async def test_geocode_returns_coordinates_and_building_id(monkeypatch):
    fake_response = FakeResponse(
        [
            {
                "lat": "59.935000",
                "lon": "30.325000",
                "osm_id": "123456",
            }
        ]
    )
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = GeocodingService()

    result = await service.geocode("Nevsky Prospect 28, St. Petersburg")

    assert result is not None
    assert result.coordinates.lat == pytest.approx(59.935)
    assert result.coordinates.lon == pytest.approx(30.325)
    assert result.building_id.osm_id == 123456
    assert fake_client.request_args["url"] == _DEFAULT_BASE_URL
    assert fake_client.request_args["params"] == {
        "q": "Nevsky Prospect 28, St. Petersburg",
        "format": "json",
        "limit": "1",
    }
    assert fake_client.request_args["headers"] == {"User-Agent": _DEFAULT_USER_AGENT}


@pytest.mark.asyncio
async def test_geocode_returns_none_when_no_results(monkeypatch):
    fake_response = FakeResponse([])
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = GeocodingService()

    assert await service.geocode("Unknown Place") is None


@pytest.mark.asyncio
async def test_geocode_raises_agent_service_error_on_http_status(monkeypatch):
    request = httpx.Request("GET", _DEFAULT_BASE_URL)
    response = httpx.Response(status_code=429, request=request)
    status_error = httpx.HTTPStatusError("Too Many Requests", request=request, response=response)
    fake_response = FakeResponse([], status_exc=status_error)
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = GeocodingService()

    with pytest.raises(OpenStreetMapServiceError) as exc_info:
        await service.geocode("Nevsky Prospect 28")

    assert exc_info.value.upstream_status == 429


@pytest.mark.asyncio
async def test_geocode_raises_agent_service_error_on_malformed_payload(monkeypatch):
    fake_response = FakeResponse(
        [
            {
                "lat": "not-a-number",
                "lon": "30.325000",
                "osm_id": "123456",
            }
        ]
    )
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = GeocodingService()

    with pytest.raises(OpenStreetMapServiceError):
        await service.geocode("Nevsky Prospect 28")


@pytest.mark.asyncio
async def test_reverse_geocode_returns_coordinates_and_building_id(monkeypatch):
    fake_response = FakeResponse(
        {
            "lat": "59.935000",
            "lon": "30.325000",
            "osm_id": "654321",
            "osm_type": "way",
        }
    )
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = GeocodingService()

    result = await service.reverse_geocode(Coordinates(lat=59.935, lon=30.325))

    assert result is not None
    assert result.coordinates.lat == pytest.approx(59.935)
    assert result.coordinates.lon == pytest.approx(30.325)
    assert result.building_id.osm_id == 654321
    assert fake_client.request_args["url"] == _DEFAULT_REVERSE_URL
    assert fake_client.request_args["params"] == {
        "lat": "59.935",
        "lon": "30.325",
        "format": "json",
        "zoom": "18",
    }
    assert fake_client.request_args["headers"] == {"User-Agent": _DEFAULT_USER_AGENT}


@pytest.mark.asyncio
async def test_reverse_geocode_returns_none_when_osm_type_not_way(monkeypatch):
    fake_response = FakeResponse(
        {
            "lat": "59.935000",
            "lon": "30.325000",
            "osm_id": "654321",
            "osm_type": "node",
        }
    )
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = GeocodingService()

    result = await service.reverse_geocode(Coordinates(lat=59.935, lon=30.325))

    assert result is None


@pytest.mark.asyncio
async def test_reverse_geocode_raises_agent_service_error_on_malformed_coordinates(monkeypatch):
    fake_response = FakeResponse(
        {
            "lat": "not-a-number",
            "lon": "30.325000",
            "osm_id": "654321",
            "osm_type": "way",
        }
    )
    fake_client = FakeAsyncClient(response=fake_response)
    _patch_async_client(monkeypatch, fake_client)

    service = GeocodingService()

    with pytest.raises(OpenStreetMapServiceError):
        await service.reverse_geocode(Coordinates(lat=59.935, lon=30.325))

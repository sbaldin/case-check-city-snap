import base64
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from citysnap.app.main import app
from citysnap.app.schemas import BuildingInfo, Coordinates, CoordinatesAndBuildingId
from citysnap.app.schemas.building import BuildingId
from citysnap.app.services import get_building_data_service, get_geocoding_service


class FakeGeocodingService:
    def __init__(self):
        self.geocode_calls: list[str] = []
        self.reverse_calls: list[Coordinates] = []

    async def geocode(self, address: str):
        self.geocode_calls.append(address)
        return None

    async def reverse_geocode(self, coordinates: Coordinates):
        self.reverse_calls.append(coordinates)
        return CoordinatesAndBuildingId(
            coordinates=coordinates,
            building_id=BuildingId(osm_id=777),
        )


class FakeBuildingDataService:
    def __init__(self):
        self.fetch_calls: list[int] = []

    async def fetch(self, *, building_id: int):
        self.fetch_calls.append(building_id)
        return BuildingInfo(name="Test Building")


@pytest.fixture
def client():
    geocoding_service = FakeGeocodingService()
    building_service = FakeBuildingDataService()

    app.dependency_overrides[get_geocoding_service] = lambda: geocoding_service
    app.dependency_overrides[get_building_data_service] = lambda: building_service

    test_client = TestClient(app)
    yield test_client, geocoding_service, building_service

    app.dependency_overrides.clear()


def test_building_info_uses_coordinates_when_present(client):
    test_client, geocoding_service, building_service = client

    response = test_client.post(
        "/api/v1/building/info",
        json={
            "coordinates": {
                "lat": 59.935,
                "lon": 30.325,
            }
        },
    )

    assert response.status_code == 200

    payload = response.json()
    assert payload["building"]["name"] == "Test Building"
    assert payload["building"]["location"] == {"lat": 59.935, "lon": 30.325}
    assert geocoding_service.geocode_calls == []
    assert len(geocoding_service.reverse_calls) == 1
    assert building_service.fetch_calls == [777]


def test_building_info_saves_base64_image(tmp_path, monkeypatch, client):
    test_client, geocoding_service, building_service = client
    monkeypatch.setenv("CITYSNAP_UPLOAD_DIR", str(tmp_path))

    encoded_image = base64.b64encode(b"sample-image").decode("ascii")

    response = test_client.post(
        "/api/v1/building/info",
        json={
            "coordinates": {"lat": 59.935, "lon": 30.325},
            "image_base64": encoded_image,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    image_path = Path(payload["building"]["image_path"])
    assert image_path.exists()
    assert image_path.read_bytes() == b"sample-image"
    assert building_service.fetch_calls == [777]


def test_building_info_requires_address_or_coordinates(client):
    test_client, _, _ = client

    response = test_client.post("/api/v1/building/info", json={})

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "OpenStreetMap gateway requires either an address or coordinates to query OpenStreetMap APIs"
    )


def test_building_info_returns_not_found_when_geocode_fails(client):
    test_client, geocoding_service, _ = client

    response = test_client.post(
        "/api/v1/building/info",
        json={"address": "Unknown Street"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "OpenStreetMap Nominatim could not resolve the provided location"
    assert geocoding_service.geocode_calls == ["Unknown Street"]
    assert geocoding_service.reverse_calls == []


def test_building_info_rejects_invalid_base64_image(client):
    test_client, _, _ = client

    response = test_client.post(
        "/api/v1/building/info",
        json={
            "coordinates": {"lat": 59.935, "lon": 30.325},
            "image_base64": "@@@invalid@@@",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "OpenStreetMap gateway cannot decode the provided base64 photo"

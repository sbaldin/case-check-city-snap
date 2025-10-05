"""Geocoding service built on top of OpenStreetMap Nominatim."""

from __future__ import annotations

import os
from typing import Any

import httpx

from ..schemas import Coordinates, CoordinatesAndBuildingId
from .exceptions import AgentServiceError
from ..schemas.building import BuildingId

_DEFAULT_BASE_URL = "https://nominatim.openstreetmap.org/search"
_DEFAULT_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
_DEFAULT_USER_AGENT = "CitySnapGateway/0.1 (+https://github.com/fesswood)"


class GeocodingService:
    """Convert addresses to coordinates via Nominatim."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        limit: int = 1,
        timeout: float = 10.0,
        reverse_url: str | None = None,
        reverse_zoom: int = 18,
    ) -> None:
        self._base_url = base_url or _DEFAULT_BASE_URL
        self._user_agent = user_agent or _DEFAULT_USER_AGENT
        self._limit = limit
        self._timeout = timeout
        self._reverse_url = reverse_url or _DEFAULT_REVERSE_URL
        self._reverse_zoom = reverse_zoom

    async def geocode(self, address: str) -> CoordinatesAndBuildingId | None:
        """Return coordinates for the provided address or ``None`` if not found."""
        params = {"q": address, "format": "json", "limit": str(self._limit)}
        headers = {"User-Agent": self._user_agent}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._base_url, params=params, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network error path
            status_code = exc.response.status_code if exc.response is not None else None
            raise AgentServiceError("Geocoding request rejected", upstream_status=status_code) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network error path
            raise AgentServiceError("Failed to call geocoding service") from exc

        data: Any
        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - response parsing path
            raise AgentServiceError("Geocoding service returned invalid JSON") from exc

        if not isinstance(data, list) or not data:
            return None

        building_geo_info = data[0]
        try:
            latitude = float(building_geo_info["lat"])
            longitude = float(building_geo_info["lon"])
            osm_id = int(building_geo_info["osm_id"])
        except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
            raise AgentServiceError("Geocoding service returned malformed coordinates") from exc

        return CoordinatesAndBuildingId(
            coordinates=Coordinates(lat=latitude, lon=longitude),
            building_id= BuildingId(osm_id=osm_id)
        )

    async def reverse_geocode(self, coordinates: Coordinates) -> CoordinatesAndBuildingId | None:
        """Return building metadata using provided coordinates."""
        params = {
            "lat": str(coordinates.lat),
            "lon": str(coordinates.lon),
            "format": "json",
            "zoom": str(self._reverse_zoom),
        }
        headers = {"User-Agent": self._user_agent}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._reverse_url, params=params, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network error path
            status_code = exc.response.status_code if exc.response is not None else None
            raise AgentServiceError("Geocoding request rejected", upstream_status=status_code) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network error path
            raise AgentServiceError("Failed to call geocoding service") from exc

        payload: Any
        try:
            payload = response.json()
        except ValueError as exc:  # pragma: no cover - response parsing path
            raise AgentServiceError("Geocoding service returned invalid JSON") from exc

        if not isinstance(payload, dict):
            return None

        osm_id_raw = payload.get("osm_id")
        osm_type = payload.get("osm_type")
        if osm_id_raw is None or osm_type not in {"way", "W"}:
            return None

        try:
            osm_id = int(osm_id_raw)
        except (TypeError, ValueError) as exc:
            raise AgentServiceError("Geocoding service returned malformed coordinates") from exc

        latitude_raw = payload.get("lat", coordinates.lat)
        longitude_raw = payload.get("lon", coordinates.lon)
        try:
            latitude = float(latitude_raw)
            longitude = float(longitude_raw)
        except (TypeError, ValueError) as exc:
            raise AgentServiceError("Geocoding service returned malformed coordinates") from exc

        return CoordinatesAndBuildingId(
            coordinates=Coordinates(lat=latitude, lon=longitude),
            building_id=BuildingId(osm_id=osm_id),
        )


def get_geocoding_service() -> GeocodingService:
    """Factory for FastAPI dependency injection."""
    base_url = os.getenv("CITYSNAP_GEOCODING_BASE_URL", _DEFAULT_BASE_URL)
    user_agent = os.getenv("CITYSNAP_GEOCODING_USER_AGENT", _DEFAULT_USER_AGENT)
    limit = int(os.getenv("CITYSNAP_GEOCODING_LIMIT", "1"))
    timeout = float(os.getenv("CITYSNAP_GEOCODING_TIMEOUT", "10.0"))
    reverse_url = os.getenv("CITYSNAP_GEOCODING_REVERSE_URL", _DEFAULT_REVERSE_URL)
    reverse_zoom = int(os.getenv("CITYSNAP_GEOCODING_REVERSE_ZOOM", "18"))
    return GeocodingService(
        base_url=base_url,
        user_agent=user_agent,
        limit=limit,
        timeout=timeout,
        reverse_url=reverse_url,
        reverse_zoom=reverse_zoom,
    )

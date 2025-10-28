"""Geocoding service built on top of OpenStreetMap Nominatim."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from ..schemas import Coordinates, CoordinatesAndBuildingId
from ..schemas.building import BuildingId
from .exceptions import OpenStreetMapServiceError

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
        self._logger = logging.getLogger(__name__)

    async def geocode(self, address: str) -> CoordinatesAndBuildingId | None:
        """Return coordinates for the provided address or ``None`` if not found."""
        params = {"q": address, "format": "json", "limit": str(self._limit)}
        headers = {"User-Agent": self._user_agent}

        try:
            self._logger.info("Calling OpenStreetMap geocoding url=%s address=%r", self._base_url, address)
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._base_url, params=params, headers=headers)
            response.raise_for_status()
            self._logger.info(
                "Geocoding response received address=%r status_code=%s",
                address,
                response.status_code,
            )
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network error path
            status_code = exc.response.status_code if exc.response is not None else None
            self._logger.exception(
                "OpenStreetMap geocoding request rejected address=%r status_code=%s",
                address,
                status_code,
            )
            raise OpenStreetMapServiceError(
                "OpenStreetMap Nominatim rejected the request",
                                            upstream_status=status_code
            ) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network error path
            self._logger.exception("Failed to call OpenStreetMap geocoding address=%r", address)
            raise OpenStreetMapServiceError("Failed to call OpenStreetMap Nominatim API") from exc

        data: Any
        try:
            data = response.json()
            self._logger.debug("Parsed geocoding payload for address=%r", address)
        except ValueError as exc:  # pragma: no cover - response parsing path
            self._logger.exception("Geocoding returned invalid JSON address=%r", address)
            raise OpenStreetMapServiceError("OpenStreetMap Nominatim returned invalid JSON") from exc

        if not isinstance(data, list) or not data:
            self._logger.info("No geocoding results for address=%r", address)
            return None

        building_geo_info = data[0]
        try:
            latitude = float(building_geo_info["lat"])
            longitude = float(building_geo_info["lon"])
            osm_id = int(building_geo_info["osm_id"])
        except (KeyError, TypeError, ValueError) as exc:  # pragma: no cover - defensive guard
            self._logger.exception("Geocoding returned malformed coordinates address=%r", address)
            raise OpenStreetMapServiceError("OpenStreetMap Nominatim returned malformed coordinates") from exc

        self._logger.info(
            "Geocoding succeeded address=%r lat=%s lon=%s osm_id=%s",
            address,
            latitude,
            longitude,
            osm_id,
        )
        return CoordinatesAndBuildingId(
            coordinates=Coordinates(lat=latitude, lon=longitude),
            building_id=BuildingId(osm_id=osm_id)
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
            self._logger.info(
                "Calling OpenStreetMap reverse geocoding url=%s lat=%s lon=%s",
                self._reverse_url,
                coordinates.lat,
                coordinates.lon,
            )
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(self._reverse_url, params=params, headers=headers)
            response.raise_for_status()
            self._logger.info(
                "Reverse geocoding response received lat=%s lon=%s status_code=%s",
                coordinates.lat,
                coordinates.lon,
                response.status_code,
            )
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network error path
            status_code = exc.response.status_code if exc.response is not None else None
            self._logger.exception(
                "OpenStreetMap reverse geocoding request rejected lat=%s lon=%s status_code=%s",
                coordinates.lat,
                coordinates.lon,
                status_code,
            )
            raise OpenStreetMapServiceError(
                "OpenStreetMap Nominatim rejected the request",
                upstream_status=status_code
            ) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network error path
            self._logger.exception(
                "Failed to call OpenStreetMap reverse geocoding lat=%s lon=%s",
                coordinates.lat,
                coordinates.lon,
            )
            raise OpenStreetMapServiceError("Failed to call OpenStreetMap Nominatim API") from exc

        payload: Any
        try:
            payload = response.json()
            self._logger.debug(
                "Parsed reverse geocoding payload lat=%s lon=%s",
                coordinates.lat,
                coordinates.lon,
            )
        except ValueError as exc:  # pragma: no cover - response parsing path
            self._logger.exception(
                "Reverse geocoding returned invalid JSON lat=%s lon=%s",
                coordinates.lat,
                coordinates.lon,
            )
            raise OpenStreetMapServiceError("OpenStreetMap Nominatim returned invalid JSON") from exc

        if not isinstance(payload, dict):
            self._logger.info(
                "Reverse geocoding returned non-dict payload lat=%s lon=%s",
                coordinates.lat,
                coordinates.lon,
            )
            return None

        osm_id_raw = payload.get("osm_id")
        osm_type = payload.get("osm_type")
        if osm_id_raw is None or osm_type not in {"way", "W"}:
            self._logger.info(
                "Reverse geocoding did not return a building lat=%s lon=%s osm_type=%s",
                coordinates.lat,
                coordinates.lon,
                osm_type,
            )
            return None

        try:
            osm_id = int(osm_id_raw)
        except (TypeError, ValueError) as exc:
            self._logger.exception(
                "Reverse geocoding returned malformed osm_id lat=%s lon=%s osm_id_raw=%r",
                coordinates.lat,
                coordinates.lon,
                osm_id_raw,
            )
            raise OpenStreetMapServiceError("OpenStreetMap Nominatim returned malformed coordinates") from exc

        latitude_raw = payload.get("lat", coordinates.lat)
        longitude_raw = payload.get("lon", coordinates.lon)
        try:
            latitude = float(latitude_raw)
            longitude = float(longitude_raw)
        except (TypeError, ValueError) as exc:
            self._logger.exception(
                "Reverse geocoding returned malformed coordinates lat=%s lon=%s latitude_raw=%r longitude_raw=%r",
                coordinates.lat,
                coordinates.lon,
                latitude_raw,
                longitude_raw,
            )
            raise OpenStreetMapServiceError("OpenStreetMap Nominatim returned malformed coordinates") from exc

        self._logger.info(
            "Reverse geocoding succeeded lat=%s lon=%s resolved_lat=%s resolved_lon=%s osm_id=%s",
            coordinates.lat,
            coordinates.lon,
            latitude,
            longitude,
            osm_id,
        )
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

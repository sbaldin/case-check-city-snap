"""Building data agent client backed by OpenStreetMap."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

import httpx

from ..schemas import BuildingInfo, Coordinates
from .exceptions import OpenStreetMapServiceError

_DEFAULT_BASE_URL = "https://www.openstreetmap.org/api/0.6"
_DEFAULT_USER_AGENT = "CitySnapGateway/0.1 (+https://github.com/fesswood)"


class BuildingDataService:
    """Retrieve metadata about buildings from the OpenStreetMap API."""

    def __init__(
        self,
        *,
        base_url: str | None = None,
        user_agent: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url or _DEFAULT_BASE_URL
        self._user_agent = user_agent or _DEFAULT_USER_AGENT
        self._timeout = timeout
        self._logger = logging.getLogger(__name__)

    async def fetch(
        self,
        *,
        building_id: Optional[int] = None,
        coordinates: Optional[Coordinates] = None,
    ) -> Optional[BuildingInfo]:
        """Return detailed building information using the provided identifiers."""
        if not building_id:
            self._logger.debug("No building_id provided, skipping building data fetch")
            return None

        url = self._build_element_url(building_id)

        headers = {"User-Agent": self._user_agent}

        try:
            self._logger.info(
                "Calling OpenStreetMap building data API url=%s osm_id=%s",
                url,
                building_id,
            )
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url, headers=headers)
            response.raise_for_status()
            self._logger.info(
                "OpenStreetMap building data API responded status_code=%s osm_id=%s",
                response.status_code,
                building_id,
            )
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure
            status_code = exc.response.status_code if exc.response is not None else None
            self._logger.exception(
                "OpenStreetMap building data API rejected the request osm_id=%s status_code=%s",
                building_id,
                status_code,
            )
            raise OpenStreetMapServiceError("OpenStreetMap building data API rejected the request", upstream_status=status_code) from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            self._logger.exception(
                "Failed to call OpenStreetMap building data API osm_id=%s",
                building_id,
            )
            raise OpenStreetMapServiceError("Failed to call OpenStreetMap building data API") from exc

        payload: Any
        try:
            payload = response.json()
            self._logger.debug("Parsed building data payload osm_id=%s", building_id)
        except ValueError as exc:  # pragma: no cover - invalid json
            self._logger.exception(
                "OpenStreetMap building data API returned invalid JSON osm_id=%s",
                building_id,
            )
            raise OpenStreetMapServiceError("OpenStreetMap building data API returned invalid JSON") from exc

        building = self._extract_building(payload, building_id)
        tags: dict[str, Any] = building.get("tags", {})

        return BuildingInfo(
            name=self._extract_name(tags),
            year_built=self._extract_year(tags),
            architect=self._extract_architect(tags),
            history=self._extract_history(tags),
        )

    def _build_element_url(self, element_id: int) -> str:
        cleaned_base = self._base_url.rstrip("/")
        return f"{cleaned_base}/node/{element_id}.json"

    def _extract_building(self, payload: Any, element_id: int) -> dict[str, Any]:
        if not isinstance(payload, dict):
            self._logger.error(
                "Unexpected payload type from building data API osm_id=%s payload_type=%s",
                element_id,
                type(payload).__name__,
            )
            raise OpenStreetMapServiceError("OpenStreetMap building data API returned an unexpected payload")

        elements = payload.get("elements")
        if not isinstance(elements, list):
            self._logger.error(
                "Unexpected elements structure from building data API osm_id=%s payload_keys=%s",
                element_id,
                list(payload.keys()),
            )
            raise OpenStreetMapServiceError("OpenStreetMap building data API returned an unexpected payload")

        for item in elements:
            if (
                isinstance(item, dict)
                and item.get("type") == "way" or item.get("type") == "node"
                and str(item.get("id")) == str(element_id)
            ):
                self._logger.debug("Matched building in payload osm_id=%s", element_id)
                return item

        self._logger.warning("Building not found in payload osm_id=%s", element_id)
        raise OpenStreetMapServiceError("Building not found in OpenStreetMap building data API response")

    def _extract_name(self, tags: dict[str, Any]) -> Optional[str]:
        name = tags.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        return None

    def _extract_year(self, tags: dict[str, Any]) -> Optional[int]:
        candidates = [
            tags.get("start_date"),
            tags.get("construction"),
            tags.get("building:date"),
        ]

        for candidate in candidates:
            if isinstance(candidate, str):
                # Make sure that year is a number
                match = re.search(r"(\d{1,4})", candidate)
                if match:
                    try:
                        return int(match.group(1))
                    except ValueError:  # pragma: no cover - defensive
                        continue
        return None

    def _extract_architect(self, tags: dict[str, Any]) -> Optional[str]:
        architect = tags.get("architect")
        if isinstance(architect, str) and architect.strip():
            return architect.strip()
        return None

    def _extract_history(self, tags: dict[str, Any]) -> Optional[str]:
        for key in ("description", "note", "wikipedia:synopsis"):
            value = tags.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None


def get_building_data_service() -> BuildingDataService:
    """Factory for FastAPI dependency injection."""
    base_url = os.getenv("CITYSNAP_BUILDING_DATA_BASE_URL", _DEFAULT_BASE_URL)
    user_agent = os.getenv("CITYSNAP_BUILDING_DATA_USER_AGENT", _DEFAULT_USER_AGENT)
    timeout = float(os.getenv("CITYSNAP_BUILDING_DATA_TIMEOUT", "10.0"))
    return BuildingDataService(base_url=base_url, user_agent=user_agent, timeout=timeout)

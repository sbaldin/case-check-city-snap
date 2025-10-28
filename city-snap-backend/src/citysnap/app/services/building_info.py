"""Orchestration logic for assembling building information responses."""

from __future__ import annotations

import base64
import binascii
import logging
from typing import Optional

from fastapi import Depends

from ..schemas import (
    BuildingInfo,
    BuildingInfoRequest,
    BuildingInfoResponse,
    Coordinates,
)
from .exceptions import (
    BuildingInfoNotFoundError,
    BuildingInfoUpstreamError,
    BuildingInfoValidationError,
    OpenStreetMapServiceError,
)
from .geocoding import GeocodingService, get_geocoding_service
from .llm_enricher import LlmBuildingInfoEnricher, get_llm_building_info_enricher
from .open_street_map import OpenStreetMapService, get_building_data_service
from .storage import ImageStorageService, get_image_storage_service

logger = logging.getLogger(__name__)

_DEFAULT_IMAGE_EXTENSION = "jpg"
_MIME_EXTENSION_MAP = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


class BuildingInfoOrchestrator:
    """Coordinate downstream services and enrichment to build a response payload."""

    def __init__(
        self,
        *,
        geocoding_service: GeocodingService,
        building_data_service: OpenStreetMapService,
        image_storage: ImageStorageService,
        llm_enricher: LlmBuildingInfoEnricher,
    ) -> None:
        self._geocoding_service = geocoding_service
        self._building_data_service = building_data_service
        self._image_storage = image_storage
        self._llm_enricher = llm_enricher

    async def build(self, payload: BuildingInfoRequest) -> BuildingInfoResponse:
        """Return aggregated building data using address, coordinates, or photo hints."""
        coordinates_payload = payload.coordinates.model_dump() if payload.coordinates else None
        logger.info(
            "Building info request received: address=%r coordinates=%s has_image=%s",
            payload.address,
            coordinates_payload,
            bool(payload.image_base64),
        )

        decoded_image = self._decode_image(payload.image_base64) if payload.image_base64 else None
        geocode_result, geocode_source = await self._resolve_geocode(payload)

        if geocode_result is None:
            logger.warning("Geocoding yielded no results")
            raise BuildingInfoNotFoundError("OpenStreetMap Nominatim could not resolve the provided location")

        try:
            coordinates: Coordinates = geocode_result.coordinates
            osm_building_id = geocode_result.building_id.osm_id
        except AttributeError as exc:  # pragma: no cover - defensive
            raise BuildingInfoUpstreamError(f"OpenStreetMap Nominatim returned an unexpected payload: "
                                            f"Malformed geocode response: ${geocode_result}") from exc

        sources: list[str] = []
        if geocode_source:
            sources.append(geocode_source)

        building = await self._fetch_building_data(osm_building_id, coordinates, sources)

        if decoded_image is not None:
            stored_image_path = self._image_storage.store(
                image_bytes=decoded_image[0],
                extension=decoded_image[1],
                building_id=osm_building_id,
                coordinates=coordinates,
            )
            building = building.model_copy(update={"image_path": stored_image_path})
            logger.info("Stored uploaded image at %s", stored_image_path)

        enriched = False
        if any(value is None for value in (building.year_built, building.architect, building.history)):
            building, enriched = await self._llm_enricher.enrich(
                building=building,
                address=payload.address,
                has_photo=decoded_image is not None,
            )
        if enriched:
            sources.append("LLM Generated")

        logger.info(
            "Returning building info response osm_id=%s sources=%s has_image=%s",
            osm_building_id,
            sources,
            bool(decoded_image),
        )
        return BuildingInfoResponse(building=building, source=sources)

    async def _resolve_geocode(self, payload: BuildingInfoRequest):
        geocode_result = None
        geocode_source: Optional[str] = None

        if payload.address:
            logger.info("Attempting geocode search for address=%r", payload.address)
            try:
                geocode_result = await self._geocoding_service.geocode(payload.address)
            except OpenStreetMapServiceError as exc:
                logger.exception("Geocode search failed for address=%r", payload.address)
                raise OpenStreetMapServiceError(
                    f"OpenStreetMap Nominatim search failed: {exc.detail}",
                    upstream_status=exc.upstream_status,
                ) from exc
            if geocode_result is not None:
                logger.info(
                    "Geocode search succeeded for address=%r -> coordinates=%s osm_id=%s",
                    payload.address,
                    geocode_result.coordinates.model_dump(),
                    geocode_result.building_id.osm_id,
                )
                geocode_source = "OpenStreetMap Nominatim (search)"

        if geocode_result is None and payload.coordinates is not None:
            logger.info(
                "Attempting reverse geocode for coordinates=%s",
                payload.coordinates.model_dump(),
            )
            try:
                geocode_result = await self._geocoding_service.reverse_geocode(payload.coordinates)
            except OpenStreetMapServiceError as exc:
                logger.exception(
                    "Reverse geocode failed for coordinates=%s",
                    payload.coordinates.model_dump(),
                )
                raise OpenStreetMapServiceError(
                    f"OpenStreetMap Nominatim reverse lookup failed: {exc.detail}",
                    upstream_status=exc.upstream_status,
                ) from exc
            if geocode_result is not None:
                logger.info(
                    "Reverse geocode succeeded for coordinates=%s -> resolved_coordinates=%s osm_id=%s",
                    payload.coordinates.model_dump(),
                    geocode_result.coordinates.model_dump(),
                    geocode_result.building_id.osm_id,
                )
                geocode_source = "OpenStreetMap Nominatim (reverse)"

        return geocode_result, geocode_source

    async def _fetch_building_data(
        self,
        osm_building_id: int,
        coordinates: Coordinates,
        sources: list[str],
    ) -> BuildingInfo:
        logger.info("Fetching building data for osm_id=%s", osm_building_id)
        try:
            building = await self._building_data_service.fetch(building_id=osm_building_id)
        except OpenStreetMapServiceError as exc:
            logger.exception("Building data lookup failed for osm_id=%s", osm_building_id)
            raise OpenStreetMapServiceError(
                f"OpenStreetMap API failed to provide building data: {exc.detail}",
                upstream_status=exc.upstream_status,
            ) from exc

        if building:
            if coordinates and not building.location:
                building = building.model_copy(update={"location": coordinates})
            sources.append("OpenStreetMap API")
            logger.info("Building data assembled for osm_id=%s sources=%s", osm_building_id, sources)
            return building

        logger.info("Building data not found, falling back to coordinates only for osm_id=%s", osm_building_id)
        return BuildingInfo(location=coordinates)

    def _decode_image(self, image_base64: str) -> tuple[bytes, str]:
        encoded = image_base64.strip()
        extension = _DEFAULT_IMAGE_EXTENSION

        if encoded.startswith("data:"):
            header, _, encoded = encoded.partition(",")
            if not encoded:
                self._raise_invalid_image("missing payload")
            mime = header.split(";")[0].split(":")[-1]
            extension = _MIME_EXTENSION_MAP.get(mime, _DEFAULT_IMAGE_EXTENSION)

        try:
            return base64.b64decode(encoded, validate=True), extension
        except (binascii.Error, ValueError):
            self._raise_invalid_image("invalid base64 data")
            raise  # pragma: no cover - unreachable

    @staticmethod
    def _raise_invalid_image(reason: str) -> None:
        logger.warning("Invalid base64 image provided: %s", reason)
        raise BuildingInfoValidationError("OpenStreetMap gateway cannot decode the provided base64 photo")

def get_building_info_orchestrator(
    geocoding_service: GeocodingService = Depends(get_geocoding_service),
    building_data_service: OpenStreetMapService = Depends(get_building_data_service),
    image_storage: ImageStorageService = Depends(get_image_storage_service),
    llm_enricher: LlmBuildingInfoEnricher = Depends(get_llm_building_info_enricher),
) -> BuildingInfoOrchestrator:
    """Factory for FastAPI dependency injection."""
    return BuildingInfoOrchestrator(
        geocoding_service=geocoding_service,
        building_data_service=building_data_service,
        image_storage=image_storage,
        llm_enricher=llm_enricher,
    )


__all__ = ["BuildingInfoOrchestrator", "get_building_info_orchestrator"]

"""Building information endpoints."""

from __future__ import annotations

import base64
import binascii
import os
from datetime import datetime
from pathlib import Path

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import BuildingInfo, BuildingInfoRequest, BuildingInfoResponse, Coordinates
from ..services import (
    OpenStreetMapServiceError,
    BuildingDataService,
    GeocodingService,
    LLMFacade,
    LLMProviderError,
    get_building_data_service,
    get_geocoding_service,
    try_get_llm_facade,
)

router = APIRouter(prefix="/api/v1", tags=["buildings"])

logger = logging.getLogger(__name__)

_UPLOAD_DIR_ENV = "CITYSNAP_UPLOAD_DIR"
_DEFAULT_UPLOAD_DIR = "uploads"
_DEFAULT_IMAGE_EXTENSION = "jpg"
_MIME_EXTENSION_MAP = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

@router.post("/building/info", response_model=BuildingInfoResponse, summary="Retrieve building information")
async def building_info(
    payload: BuildingInfoRequest,
    geocoding_service: GeocodingService = Depends(get_geocoding_service),
    building_data_service: BuildingDataService = Depends(get_building_data_service),
    llm_facade: LLMFacade | None = Depends(try_get_llm_facade)
) -> BuildingInfoResponse:
    """Orchestrate downstream requests to construct a building profile."""
    coordinates_payload = payload.coordinates.model_dump() if payload.coordinates else None
    logger.info(
        "Building info request received: address=%r coordinates=%s has_image=%s",
        payload.address,
        coordinates_payload,
        bool(payload.image_base64),
    )
    if not payload.address and payload.coordinates is None:
        logger.warning("Validation error: missing address and coordinates")
        raise HTTPException(
            status_code=400,
            detail="OpenStreetMap gateway requires either an address or coordinates to query OpenStreetMap APIs",
        )

    sources: list[str] = []

    geocode_result = None
    geocode_source: str | None = None
    decoded_image: tuple[bytes, str] | None = None

    if payload.image_base64:
        try:
            decoded_image = _decode_image(payload.image_base64)
        except ValueError as exc:
            logger.warning("Invalid base64 image provided", exc_info=exc)
            raise HTTPException(
                status_code=400,
                detail="OpenStreetMap gateway cannot decode the provided base64 photo",
            ) from exc

    if payload.address:
        logger.info("Attempting geocode search for address=%r", payload.address)
        try:
            geocode_result = await geocoding_service.geocode(payload.address)
        except OpenStreetMapServiceError as exc:
            logger.exception("Geocode search failed for address=%r", payload.address)
            raise HTTPException(status_code=502, detail=f"OpenStreetMap Nominatim search failed: {exc}") from exc
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
            geocode_result = await geocoding_service.reverse_geocode(payload.coordinates)
        except OpenStreetMapServiceError as exc:
            logger.exception(
                "Reverse geocode failed for coordinates=%s",
                payload.coordinates.model_dump(),
            )
            raise HTTPException(status_code=502, detail=f"OpenStreetMap Nominatim reverse lookup failed: {exc}") from exc
        if geocode_result is not None:
            logger.info(
                "Reverse geocode succeeded for coordinates=%s -> resolved_coordinates=%s osm_id=%s",
                payload.coordinates.model_dump(),
                geocode_result.coordinates.model_dump(),
                geocode_result.building_id.osm_id,
            )
            geocode_source = "OpenStreetMap Nominatim (reverse)"

    if geocode_result is None:
        logger.warning("Geocoding yielded no results")
        raise HTTPException(status_code=404, detail="OpenStreetMap Nominatim could not resolve the provided location")

    try:
        coordinates: Coordinates = geocode_result.coordinates
        osm_building_id = geocode_result.building_id.osm_id
    except AttributeError as exc:  # pragma: no cover - defensive
        logger.exception("Malformed geocode response: %r", geocode_result)
        raise HTTPException(status_code=502, detail="OpenStreetMap Nominatim returned an unexpected payload") from exc

    if geocode_source:
        sources.append(geocode_source)

    logger.info("Fetching building data for osm_id=%s", osm_building_id)
    try:
        building = await building_data_service.fetch(building_id=osm_building_id)
    except OpenStreetMapServiceError as exc:
        logger.exception("Building data lookup failed for osm_id=%s", osm_building_id)
        raise HTTPException(status_code=502, detail=f"OpenStreetMap API failed to provide building data: {exc}") from exc

    if building:
        # make sure coordinates discovered from geocoding are included
        if coordinates and not building.location:
            building = building.model_copy(update={"location": coordinates})
        sources.append("OpenStreetMap API")
        logger.info("Building data assembled for osm_id=%s sources=%s", osm_building_id, sources)
    else:
        building = BuildingInfo(location=coordinates)
        logger.info("Building data not found, falling back to coordinates only for osm_id=%s", osm_building_id)

    if decoded_image is not None:
        stored_image_path = _persist_image(
            image_bytes=decoded_image[0],
            extension=decoded_image[1],
            building_id=osm_building_id,
            coordinates=coordinates,
        )
        building = building.model_copy(update={"image_path": stored_image_path})
        logger.info("Stored uploaded image at %s", stored_image_path)

    if any(value is None for value in (building.year_built, building.architect, building.history)):
        updated_building = await _enrich_building_info_by_lmm(
            llm_facade=llm_facade,
            address=payload.address,
            building=building,
            has_photo=decoded_image is not None,
        )
        if updated_building != building:
            building = updated_building
            sources.append("LLM Generated")

    if not sources:
        sources.append("Gateway Stub")

    logger.info(
        "Returning building info response osm_id=%s sources=%s has_image=%s",
        osm_building_id,
        sources,
        bool(decoded_image),
    )
    return BuildingInfoResponse(building=building, source=sources)


def _decode_image(image_base64: str) -> tuple[bytes, str]:
    """Decode base64 payload; return image bytes and an extension hint."""
    encoded = image_base64.strip()
    extension = _DEFAULT_IMAGE_EXTENSION

    if encoded.startswith("data:"):
        header, _, encoded = encoded.partition(",")
        if not encoded:
            raise ValueError("missing base64 payload")
        mime = header.split(";")[0].split(":")[-1]
        extension = _MIME_EXTENSION_MAP.get(mime, _DEFAULT_IMAGE_EXTENSION)

    try:
        return base64.b64decode(encoded, validate=True), extension
    except (binascii.Error, ValueError) as exc:
        raise ValueError("invalid base64 data") from exc


def _persist_image(
        *,
        image_bytes: bytes,
        extension: str,
        building_id: int | None,
        coordinates: Coordinates | None,
) -> str:
    """Store decoded image bytes under uploads directory."""
    upload_dir = Path(os.getenv(_UPLOAD_DIR_ENV, _DEFAULT_UPLOAD_DIR))

    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.exception("Failed to prepare uploads directory %s", upload_dir)
        raise HTTPException(
            status_code=500,
            detail="OpenStreetMap gateway cannot prepare the uploads directory",
        ) from exc

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    parts: list[str] = []
    if building_id is not None:
        parts.append(f"osm-{building_id}")
    if coordinates is not None:
        parts.append(f"{coordinates.lat:.3f}-{coordinates.lon:.3f}")
    if not parts:
        parts.append("osm")

    filename = f"{'_'.join(parts)}_{timestamp}.{extension}"
    path = upload_dir / filename

    try:
        path.write_bytes(image_bytes)
    except OSError as exc:
        logger.exception("Failed to store uploaded image at %s", path)
        raise HTTPException(
            status_code=500,
            detail="OpenStreetMap gateway failed to store the uploaded photo",
        ) from exc

    return f"/uploads/{filename}"


async def _enrich_building_info_by_lmm(
    *,
    llm_facade: LLMFacade | None,
    address: str | None,
    building: BuildingInfo,
    has_photo: bool,
) -> BuildingInfo | None:
    """Attempt to enrich building metadata using configured LLM facade."""
    if llm_facade is None:
        logger.info("LLM facade not configured; skipping enrichment")
        return None

    photo_context = "Пользователь предоставил фотографию здания" if has_photo else "фотография отсутствует"
    address_hint = address or _build_address_hint(building)

    try:
        llm_result = await llm_facade.query_building_info(
            address=address_hint,
            photo_context=photo_context,
        )

        if llm_result is not None:
            updates = {}
            if building.year_built is None and llm_result.year_built is not None:
                updates["year_built"] = llm_result.year_built
            if building.architect is None and llm_result.architect is not None:
                updates["architect"] = llm_result.architect
            if building.history is None and llm_result.history is not None:
                updates["history"] = llm_result.history
            if updates:
                building = building.model_copy(update=updates)
        return building
    except LLMProviderError as exc:
        logger.warning("LLM provider failed to enrich response: %s", exc)
        return building


def _build_address_hint(building: BuildingInfo) -> str:
    """Craft a minimal address hint when the original payload omitted one."""
    if building.location:
        return f"координаты lat={building.location.lat}, lon={building.location.lon}"
    return "не указан"

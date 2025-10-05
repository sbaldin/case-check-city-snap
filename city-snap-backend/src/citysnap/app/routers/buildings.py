"""Building information endpoints."""

from __future__ import annotations

import base64
import binascii
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import BuildingInfo, BuildingInfoRequest, BuildingInfoResponse, Coordinates
from ..services import (
    OpenStreetMapServiceError,
    BuildingDataService,
    GeocodingService,
    get_building_data_service,
    get_geocoding_service,
)

router = APIRouter(prefix="/api/v1", tags=["buildings"])

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
) -> BuildingInfoResponse:
    """Orchestrate downstream requests to construct a building profile."""
    if not payload.address and payload.coordinates is None:
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
            raise HTTPException(
                status_code=400,
                detail="OpenStreetMap gateway cannot decode the provided base64 photo",
            ) from exc

    if payload.address:
        try:
            geocode_result = await geocoding_service.geocode(payload.address)
        except OpenStreetMapServiceError as exc:
            raise HTTPException(status_code=502, detail=f"OpenStreetMap Nominatim search failed: {exc}") from exc
        if geocode_result is not None:
            geocode_source = "OpenStreetMap Nominatim (search)"

    if geocode_result is None and payload.coordinates is not None:
        try:
            geocode_result = await geocoding_service.reverse_geocode(payload.coordinates)
        except OpenStreetMapServiceError as exc:
            raise HTTPException(status_code=502, detail=f"OpenStreetMap Nominatim reverse lookup failed: {exc}") from exc
        if geocode_result is not None:
            geocode_source = "OpenStreetMap Nominatim (reverse)"

    if geocode_result is None:
        raise HTTPException(status_code=404, detail="OpenStreetMap Nominatim could not resolve the provided location")

    try:
        coordinates: Coordinates = geocode_result.coordinates
        osm_building_id = geocode_result.building_id.osm_id
    except AttributeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="OpenStreetMap Nominatim returned an unexpected payload") from exc

    if geocode_source:
        sources.append(geocode_source)

    try:
        building = await building_data_service.fetch(building_id=osm_building_id)
    except OpenStreetMapServiceError as exc:
        raise HTTPException(status_code=502, detail=f"OpenStreetMap API failed to provide building data: {exc}") from exc

    if building:
        # make sure coordinates discovered from geocoding are included
        if coordinates and not building.location:
            building = building.model_copy(update={"location": coordinates})
        sources.append("OpenStreetMap API")
    else:
        building = BuildingInfo(location=coordinates)

    if decoded_image is not None:
        stored_image_path = _persist_image(
            image_bytes=decoded_image[0],
            extension=decoded_image[1],
            building_id=osm_building_id,
            coordinates=coordinates,
        )
        building = building.model_copy(update={"image_path": stored_image_path})

    if not sources:
        sources.append("Gateway Stub")

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
        raise HTTPException(
            status_code=500,
            detail="OpenStreetMap gateway cannot prepare the uploads directory",
        ) from exc

    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    parts: list[str] = []
    if building_id is not None:
        parts.append(f"osm-{building_id}")
    if coordinates is not None:
        parts.append(f"{coordinates.lat:.6f}-{coordinates.lon:.6f}")
    if not parts:
        parts.append("osm")

    filename = f"{'_'.join(parts)}_{timestamp}.{extension}"
    path = upload_dir / filename

    try:
        path.write_bytes(image_bytes)
    except OSError as exc:
        raise HTTPException(
            status_code=500,
            detail="OpenStreetMap gateway failed to store the uploaded photo",
        ) from exc

    return str(path.resolve())

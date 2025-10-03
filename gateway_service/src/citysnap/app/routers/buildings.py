"""Building information endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import BuildingInfo, BuildingInfoRequest, BuildingInfoResponse, Coordinates
from ..services import (
    AgentServiceError,
    BuildingDataService,
    GeocodingService,
    get_building_data_service,
    get_geocoding_service,
)

router = APIRouter(prefix="/api/v1", tags=["buildings"])


@router.post("/building/info", response_model=BuildingInfoResponse, summary="Retrieve building information")
async def building_info(
        payload: BuildingInfoRequest,
        geocoding_service: GeocodingService = Depends(get_geocoding_service),
        building_data_service: BuildingDataService = Depends(get_building_data_service),
) -> BuildingInfoResponse:
    """Orchestrate downstream agents to construct a building profile."""
    if not payload.address and payload.coordinates is None:
        raise HTTPException(
            status_code=400,
            detail="Either address or coordinates must be provided",
        )

    sources: list[str] = []

    geocode_result = None
    geocode_source: str | None = None

    if payload.address:
        try:
            geocode_result = await geocoding_service.geocode(payload.address)
        except AgentServiceError as exc:
            raise HTTPException(status_code=502, detail=f"OpenStreetMap Nominatim search failed: {exc}") from exc
        if geocode_result is not None:
            geocode_source = "OpenStreetMap Nominatim (search)"

    if geocode_result is None and payload.coordinates is not None:
        try:
            geocode_result = await geocoding_service.reverse_geocode(payload.coordinates)
        except AgentServiceError as exc:
            raise HTTPException(status_code=502, detail=f"OpenStreetMap Nominatim reverse lookup failed: {exc}") from exc
        if geocode_result is not None:
            geocode_source = "OpenStreetMap Nominatim (reverse)"

    if geocode_result is None:
        raise HTTPException(status_code=404, detail="OpenStreetMap Nominatim could not resolve the provided location")

    try:
        coordinates: Coordinates = geocode_result.coordinates
        building_id = geocode_result.building_id
    except AttributeError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=502, detail="OpenStreetMap Nominatim returned an unexpected payload") from exc

    if geocode_source:
        sources.append(geocode_source)

    try:
        building = await building_data_service.fetch(building_id=building_id.osm_id)
    except AgentServiceError as exc:
        raise HTTPException(status_code=502, detail=f"OpenStreetMap API failed to provide building data: {exc}") from exc

    if building:
        # make sure coordinates discovered from geocoding are included
        if coordinates and not building.location:
            building = building.model_copy(update={"location": coordinates})
        sources.append("OpenStreetMap API")
    else:
        building = BuildingInfo(location=coordinates)

    if not sources:
        sources.append("Gateway Stub")

    return BuildingInfoResponse(building=building, source=sources)

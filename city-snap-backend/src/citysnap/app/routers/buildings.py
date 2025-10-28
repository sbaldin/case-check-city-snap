"""Building information endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import BuildingInfoRequest, BuildingInfoResponse
from ..services.building_info import (
    BuildingInfoOrchestrator,
    get_building_info_orchestrator,
)
from ..services.exceptions import BuildingInfoOrchestratorError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["buildings"])


@router.post("/building/info", response_model=BuildingInfoResponse, summary="Retrieve building information")
async def building_info(
    payload: BuildingInfoRequest,
    orchestrator: BuildingInfoOrchestrator = Depends(get_building_info_orchestrator),
) -> BuildingInfoResponse:
    """Return enriched building metadata obtained from downstream agents."""
    if not payload.address and payload.coordinates is None:
        logger.warning("Validation error: missing address and coordinates")
        raise HTTPException(
            status_code=400,
            detail="OpenStreetMap gateway requires either an address or coordinates to query OpenStreetMap APIs",
        )

    try:
        return await orchestrator.build(payload)
    except BuildingInfoOrchestratorError as exc:
        logger.warning("Building info orchestration failed: %s", exc)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

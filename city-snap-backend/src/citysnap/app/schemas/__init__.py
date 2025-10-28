"""Pydantic schemas exposed by the CitySnap application."""

from .building import (
    BuildingInfo,
    BuildingInfoRequest,
    BuildingInfoResponse,
    Coordinates,
    CoordinatesAndBuildingId,
)

__all__ = [
    "BuildingInfo",
    "BuildingInfoRequest",
    "BuildingInfoResponse",
    "Coordinates",
    "CoordinatesAndBuildingId",
]

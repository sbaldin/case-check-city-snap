"""Pydantic models for building-related endpoints."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class BuildingId(BaseModel):
    osm_id: int = Field(..., ge=0)


class CoordinatesAndBuildingId(BaseModel):
    coordinates: Coordinates
    building_id: BuildingId


class BuildingInfoRequest(BaseModel):
    address: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    image_base64: Optional[str] = None


class BuildingInfo(BaseModel):
    name: Optional[str] = None
    year_built: Optional[int] = None
    architect: Optional[str] = None
    location: Optional[Coordinates] = None
    history: Optional[str] = None


class BuildingInfoResponse(BaseModel):
    building: BuildingInfo
    source: List[str] = Field(default_factory=lambda: ["Stub", "OpenStreetMap (planned)", "Wikipedia (planned)"])

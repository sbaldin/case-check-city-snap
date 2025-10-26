"""Reusable storage helpers for persisting uploaded assets."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from ..schemas import Coordinates

logger = logging.getLogger(__name__)

_UPLOAD_DIR_ENV = "CITYSNAP_UPLOAD_DIR"
_DEFAULT_UPLOAD_DIR = "uploads"


class ImageStorageService:
    """Persist decoded image bytes and return the absolute filesystem path."""

    def __init__(self, base_path: Optional[Path] = None) -> None:
        self._base_path = (base_path or Path(os.getenv(_UPLOAD_DIR_ENV, _DEFAULT_UPLOAD_DIR))).resolve()

    def store(
        self,
        *,
        image_bytes: bytes,
        extension: str,
        building_id: int | None,
        coordinates: Coordinates | None,
    ) -> str:
        """Persist bytes under a deterministic filename derived from context metadata."""
        try:
            self._base_path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - filesystem failure
            logger.exception("Failed to prepare uploads directory %s", self._base_path)
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
        destination = self._base_path / filename

        try:
            destination.write_bytes(image_bytes)
        except OSError as exc:  # pragma: no cover - filesystem failure
            logger.exception("Failed to store uploaded image at %s", destination)
            raise HTTPException(
                status_code=500,
                detail="OpenStreetMap gateway failed to store the uploaded photo",
            ) from exc

        return str(destination)


def get_image_storage_service() -> ImageStorageService:
    """Factory for FastAPI dependency injection."""
    return ImageStorageService()


__all__ = ["ImageStorageService", "get_image_storage_service"]

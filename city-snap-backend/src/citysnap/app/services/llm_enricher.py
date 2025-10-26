"""Service responsible for enriching building info with LLM responses."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends

from ..schemas import BuildingInfo
from .llm import LLMFacade, LLMProviderError, try_get_llm_facade

logger = logging.getLogger(__name__)


class LlmBuildingInfoEnricher:
    """Wrapper around the LLM facade that produces building metadata updates."""

    def __init__(self, llm_facade: Optional[LLMFacade]) -> None:
        self._llm_facade = llm_facade

    async def enrich(
        self,
        *,
        building: BuildingInfo,
        address: Optional[str],
        has_photo: bool,
    ) -> tuple[BuildingInfo, bool]:
        """Return updated building info and flag whether enrichment occurred."""
        if self._llm_facade is None:
            logger.info("LLM facade not configured; skipping enrichment")
            return building, False

        photo_context = "Пользователь предоставил фотографию здания" if has_photo else "фотография отсутствует"
        address_hint = address or _build_address_hint(building)

        try:
            llm_result = await self._llm_facade.query_building_info(
                address=address_hint,
                photo_context=photo_context,
            )
        except LLMProviderError as exc:
            logger.warning("LLM provider failed to enrich response: %s", exc)
            return building, False

        if llm_result is None:
            return building, False

        updates = {}
        if building.year_built is None and llm_result.year_built is not None:
            updates["year_built"] = llm_result.year_built
        if building.architect is None and llm_result.architect is not None:
            updates["architect"] = llm_result.architect
        if building.history is None and llm_result.history is not None:
            updates["history"] = llm_result.history

        if not updates:
            return building, False

        return building.model_copy(update=updates), True


def _build_address_hint(building: BuildingInfo) -> str:
    if building.location:
        return f"координаты lat={building.location.lat}, lon={building.location.lon}"
    return "не указан"


def get_llm_building_info_enricher(
    llm_facade: Optional[LLMFacade] = Depends(try_get_llm_facade),
) -> LlmBuildingInfoEnricher:
    """Factory for FastAPI dependency injection."""
    return LlmBuildingInfoEnricher(llm_facade=llm_facade)


__all__ = ["LlmBuildingInfoEnricher", "get_llm_building_info_enricher"]

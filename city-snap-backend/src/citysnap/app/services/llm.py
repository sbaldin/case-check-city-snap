"""LLM facade and provider abstractions for building metadata enrichment."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Protocol, Sequence

from ..settings import AppSettings, get_app_settings
from .exceptions import LLMNotConfiguredError, LLMProviderError
from .llm_providers import OpenAILLMProvider

logger = logging.getLogger(__name__)

PROMPT_SYSTEM = (
    "Ты — БОТ и историк-эксперт и исследователь архитектуры. "
    "Твоя задача — по адресу и описанию (фотографии) здания предоставить:\n"
    "1) Год постройки (если известно),\n"
    "2) Имя архитектора (если известно),\n"
    "3) Краткую историческую справку (описание истории здания, значимые события, стиль)(максимум 3 предложения).\n"
    "Если ты не уверен в каком-то факте, укажи «неизвестно». Не пытайся продолжать диалог. \n"
    "Формат ответа: JSON с полями: `year`, `architect`, `history`, `sources`."
)

PROMPT_USER_TEMPLATE = (
    "Адрес: {address}\n"
    "{photo_section}"
    "Пожалуйста, верни JSON с полями: `year`, `architect`, `history`, `sources`.\n"
)

class LLMProvider(Protocol):
    """Protocol describing the minimal LLM interface expected by the facade."""

    async def generate(self, *, messages: Sequence[Dict[str, str]]) -> str:
        """Return raw model output for the provided chat messages."""


@dataclass(frozen=True)
class LLMQueryResult:
    """Canonical representation of LLM-sourced building metadata."""

    year_built: Optional[int]
    architect: Optional[str]
    history: Optional[str]
    sources: List[str]


class LLMFacade:
    """High-level API hiding prompt construction and response parsing details."""

    def __init__(self, providers: Dict[str, LLMProvider], default_provider: str) -> None:
        if not providers:
            raise ValueError("LLMFacade requires at least one provider")
        if default_provider not in providers:
            raise ValueError("Default provider must be present in providers mapping")

        self._providers = providers
        self._default_provider = default_provider

    @property
    def available_providers(self) -> List[str]:
        """Return the ordered list of configured provider names."""
        return list(self._providers.keys())

    @property
    def default_provider(self) -> str:
        return self._default_provider

    async def query_building_info(
        self,
        *,
        address: Optional[str],
        photo_context: Optional[str],
        provider_name: Optional[str] = None,
    ) -> Optional[LLMQueryResult]:
        """Query the currently selected provider and return structured output."""
        provider_key = self._select_provider(provider_name)
        messages = self._build_prompt(address=address, photo_context=photo_context)

        logger.info(
            "Querying LLM provider=%s for address=%r has_photo_context=%s",
            provider_key,
            address,
            bool(photo_context),
        )
        provider = self._providers[provider_key]

        try:
            raw_response = await provider.generate(messages=messages)
        except LLMProviderError:
            raise
        except Exception as exc:  # pragma: no cover - defensive catch-all
            logger.exception("LLM provider %s failed to generate response", provider_key)
            raise LLMProviderError(f"Provider {provider_key} failed: {exc}") from exc

        return self._parse_response(raw_response)

    def _select_provider(self, provider_name: Optional[str]) -> str:
        if provider_name:
            normalized = provider_name.lower()
            if normalized in self._providers:
                return normalized
            logger.warning(
                "Requested LLM provider %r is not configured; falling back to default",
                provider_name,
            )
        return self._default_provider

    @staticmethod
    def _build_prompt(*, address: Optional[str], photo_context: Optional[str]) -> List[Dict[str, str]]:
        photo_section = ""
        if photo_context:
            photo_section = f"Описание фото: {photo_context}\n"

        user_prompt = PROMPT_USER_TEMPLATE.format(
            address=address or "не указан",
            photo_section=photo_section,
        )
        return [
            {"role": "system", "content": PROMPT_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _parse_response(raw_response: str) -> Optional[LLMQueryResult]:
        if not raw_response or not raw_response.strip():
            logger.warning("LLM response was empty")
            return None
        try:
            payload = json.loads(raw_response)
        except json.JSONDecodeError:
            logger.warning("LLM response was not valid JSON: %s", raw_response)
            return None

        if not isinstance(payload, dict):
            logger.warning("LLM JSON payload is not an object: %s", payload)
            return None

        year_built = _normalize_year(payload.get("year"))
        architect = _normalize_optional_str(payload.get("architect"))
        history = _normalize_optional_str(payload.get("history"))
        sources = _normalize_sources(payload.get("sources"))

        return LLMQueryResult(
            year_built=year_built,
            architect=architect,
            history=history,
            sources=sources,
        )


def _normalize_year(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if not lowered or "неизвестно" in lowered or "unknown" in lowered:
            return None
        match = re.search(r"(1[0-9]{3}|20[0-9]{2})", lowered)
        if match:
            try:
                return int(match.group(0))
            except ValueError:
                return None
    return None


def _normalize_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        lowered = stripped.lower()
        if lowered in {"неизвестно", "unknown", "не удалось найти"}:
            return None
        return stripped
    return None


def _normalize_sources(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    result: List[str] = []
    for item in value:
        if isinstance(item, str):
            candidate = item.strip()
            if candidate:
                result.append(candidate)
    return result


def _build_llm_facade(open_api_key: Optional[str], giga_chat_api_key: Optional[str]) -> LLMFacade:
    """Build an `LLMFacade` from provided API keys."""
    providers: Dict[str, LLMProvider] = {}
    default_provider: Optional[str] = None

    if open_api_key:
        providers["openai"] = OpenAILLMProvider(api_key=open_api_key)
        if default_provider is None:
            default_provider = "openai"

    if not providers or default_provider is None:
        raise LLMNotConfiguredError(
            "No LLM providers configured. Set OPEN_API_KEY and/or GIGA_CHAT_API_KEY."
        )

    return LLMFacade(providers=providers, default_provider=default_provider)


@lru_cache(maxsize=1)
def _build_llm_facade_cached(open_api_key: Optional[str], giga_chat_api_key: Optional[str]) -> LLMFacade:
    return _build_llm_facade(open_api_key, giga_chat_api_key)


def get_llm_facade(settings: Optional[AppSettings] = None) -> LLMFacade:
    """Return a cached LLMFacade instance configured via application settings."""
    settings = settings or get_app_settings()
    return _build_llm_facade_cached(settings.open_api_key, settings.giga_chat_api_key)


def try_get_llm_facade() -> Optional[LLMFacade]:
    """Return a cached LLMFacade, or None when no providers are configured."""
    try:
        return get_llm_facade()
    except LLMNotConfiguredError:
        return None


def reset_llm_facade_cache() -> None:
    """Helper used in tests to clear the cached facade instance."""
    _build_llm_facade_cached.cache_clear()


__all__ = [
    "LLMFacade",
    "LLMProvider",
    "LLMProviderError",
    "LLMQueryResult",
    "LLMNotConfiguredError",
    "OpenAILLMProvider",
    "get_llm_facade",
    "try_get_llm_facade",
    "reset_llm_facade_cache",
]

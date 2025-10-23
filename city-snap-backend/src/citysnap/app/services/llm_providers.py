"""Concrete LLM provider implementations used by the gateway service."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Sequence

import httpx

from .exceptions import LLMProviderError

_OPENAI_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_OPENAI_DEFAULT_MODEL = "gpt-5-mini-2025-08-07"
_OPENAI_RESPONSES_ENDPOINT = "/responses"
_DEFAULT_TOOLS = [
    {
        "type": "web_search",
        "user_location": {
            "type": "approximate",
            "country": "RU",
            "city": "Kemerovo",
            "region": "Kemerovo",
        },
    }
]

logger = logging.getLogger(__name__)


def _extract_response_text(payload: Dict[str, Any]) -> str:
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            fragments: List[str] = []
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") in {"text", "output_text"}:
                    text_value = block.get("text")
                    if isinstance(text_value, str):
                        fragments.append(text_value)
            if fragments:
                return "".join(fragments)

    direct_content = payload.get("content")
    if isinstance(direct_content, str) and direct_content.strip():
        return direct_content

    raise LLMProviderError("OpenAI responses payload missing text content")


def _normalize_messages(messages: Sequence[Dict[str, str]]) -> List[Dict[str, str]]:
    if not isinstance(messages, Sequence):  # pragma: no cover - defensive branch
        raise LLMProviderError("`messages` must be a sequence of dict objects")

    normalized: List[Dict[str, str]] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise LLMProviderError(f"Message at index {index} is not a mapping")

        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not role.strip():
            raise LLMProviderError(f"Message at index {index} is missing a valid role")
        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError(f"Message at index {index} is missing text content")

        normalized.append({"role": role, "content": content})
    return normalized


class OpenAILLMProvider:
    """Async client for the OpenAI Responses API using plain HTTP calls."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 120.0,
        tools: List[Dict[str, Any]] | None = None,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("OpenAI provider requires a non-empty API key")

        self._api_key = api_key.strip()
        self._base_url = (base_url or _OPENAI_DEFAULT_BASE_URL).rstrip("/")
        self._model = model or _OPENAI_DEFAULT_MODEL
        self._timeout = timeout
        self._tools = tools[:] if tools is not None else list(_DEFAULT_TOOLS)

    async def generate(self, *, messages: Sequence[Dict[str, str]]) -> str:
        payload = {
            "model": self._model,
            "input": _normalize_messages(messages),
            "tools": self._tools,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "OpenAI-Beta": "responses-v1",
        }

        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout) as client:
                response = await client.post(_OPENAI_RESPONSES_ENDPOINT, json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:  # pragma: no cover - network failure path
            raise LLMProviderError(f"OpenAI responses request failed: {exc}") from exc
        except httpx.HTTPError as exc:  # pragma: no cover - network failure path
            req = getattr(exc, 'request', None)
            where = f" during {req.method} {req.url}" if req else ""
            raise LLMProviderError(f"OpenAI responses request error{where}: {exc!r}") from exc

        try:
            data = response.json()
        except ValueError as exc:  # pragma: no cover - unexpected payload
            raise LLMProviderError(f"OpenAI responses returned invalid JSON: {exc}") from exc

        return _extract_response_text(data)
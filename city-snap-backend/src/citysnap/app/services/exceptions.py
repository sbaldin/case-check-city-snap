"""Exceptions used across service integrations."""

from __future__ import annotations


class BuildingInfoOrchestratorError(RuntimeError):
    """Base error for orchestration flows that maps to an HTTP response."""

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = message


class BuildingInfoValidationError(BuildingInfoOrchestratorError):
    """Raised when a client payload fails validation."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message, status_code=status_code)


class BuildingInfoNotFoundError(BuildingInfoOrchestratorError):
    """Raised when the requested building cannot be located."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class BuildingInfoUpstreamError(BuildingInfoOrchestratorError):
    """Raised when a downstream agent returns an unexpected response."""

    def __init__(self, message: str, *, upstream_status: int | None = None) -> None:
        super().__init__(message, status_code=502)
        self.upstream_status = upstream_status


class OpenStreetMapServiceError(BuildingInfoUpstreamError):
    """Raised when a downstream agent cannot fulfill a request."""

    def __init__(self, message: str, *, upstream_status: int | None = None) -> None:
        super().__init__(message, upstream_status=upstream_status)


class LLMProviderError(BuildingInfoUpstreamError):
    """Raised when a downstream LLM provider request fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)

class LLMNotConfiguredError(RuntimeError):
    """Raised when no LLM providers are configured for the application."""

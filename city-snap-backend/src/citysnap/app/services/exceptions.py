"""Exceptions used across service integrations."""

from __future__ import annotations


class OpenStreetMapServiceError(RuntimeError):
    """Raised when a downstream agent cannot fulfill a request."""

    def __init__(self, message: str, *, upstream_status: int | None = None) -> None:
        super().__init__(message)
        self.upstream_status = upstream_status

"""Shared dependencies for the CitySnap application."""

from fastapi import Header, HTTPException


async def verify_service_token(x_token: str = Header(default="")) -> None:
    """Basic placeholder dependency for future protected routes."""
    if x_token and x_token != "dev-token":
        raise HTTPException(status_code=400, detail="Invalid X-Token header")

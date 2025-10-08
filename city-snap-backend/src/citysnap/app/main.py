"""Application entrypoint following FastAPI bigger applications layout."""

import logging

from fastapi import FastAPI
from .routers import buildings, health
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

app = FastAPI(title="CitySnap: Guide-Architect Gateway Service", version="0.1.0")

app.include_router(health.router)
app.include_router(buildings.router)

__all__ = ["app", "run"]


def run() -> None:
    """Entrypoint for `poetry run api`."""
    import uvicorn

    print("Start")
    uvicorn.run("citysnap.app.main:app", host="0.0.0.0", port=8081, reload=True)

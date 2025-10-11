"""Application entrypoint following FastAPI bigger applications layout."""

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routers import buildings, health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)

app = FastAPI(title="CitySnap: Guide-Architect Gateway Service", version="0.1.0")

_UPLOAD_DIR_ENV = "CITYSNAP_UPLOAD_DIR"
_DEFAULT_UPLOAD_DIR = "uploads"
upload_dir = Path(os.getenv(_UPLOAD_DIR_ENV, _DEFAULT_UPLOAD_DIR)).resolve()
upload_dir.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

app.include_router(health.router)
app.include_router(buildings.router)

__all__ = ["app", "run"]


def run() -> None:
    """Entrypoint for `poetry run api`."""
    import uvicorn

    print("Start")
    uvicorn.run("citysnap.app.main:app", host="0.0.0.0", port=8081, reload=True)

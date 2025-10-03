"""Application entrypoint following FastAPI bigger applications layout."""

from fastapi import FastAPI

from .routers import buildings, health

app = FastAPI(title="CitySnap: Guide-Architect Gateway Service", version="0.1.0")

app.include_router(health.router)
app.include_router(buildings.router)

__all__ = ["app", "run"]


def run() -> None:
    """Entrypoint for `poetry run api`."""
    import uvicorn

    print("Start")
    uvicorn.run("citysnap.app.main:app", host="0.0.0.0", port=8081, reload=True)

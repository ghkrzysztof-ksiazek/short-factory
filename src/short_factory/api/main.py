from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from short_factory.api.media import router as media_router
from short_factory.api.metrics import router as metrics_router
from short_factory.api.routes import router
from short_factory.api.ui import partials_router, ui_router
from short_factory.config.logging import setup_logging
from short_factory.config.settings import settings

setup_logging(settings.log_level)

app = FastAPI(title="Short Factory", version="0.1.0", description="AI YouTube Shorts production pipeline")
app.include_router(router)
app.include_router(media_router)
app.include_router(metrics_router)
app.include_router(ui_router)
app.include_router(partials_router)

_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/admin/static", StaticFiles(directory=str(_STATIC_DIR)), name="admin-static")


def run():
    import uvicorn

    uvicorn.run("short_factory.api.main:app", host="0.0.0.0", port=8000, reload=True)

"""FastAPI application factory: all routers + static assets."""

from __future__ import annotations

import mimetypes

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app import config
from app.routes import access, audit, explorer, lots, operations, redteam, verify

mimetypes.add_type("application/javascript", ".js")


def create_app() -> FastAPI:
    app = FastAPI(title=config.app_title(), docs_url="/docs", redoc_url=None)
    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(verify.router)
    app.include_router(operations.router)
    app.include_router(explorer.router)
    app.include_router(redteam.router)
    app.include_router(lots.router)
    app.include_router(access.router)
    app.include_router(audit.router)
    return app


app = create_app()

"""FastAPI entry point.

Run with:
    uvicorn server.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server import __version__
from server.api import auth, profile
from server.config import Settings, get_settings
from server.errors import install_error_handlers
from server.logging_config import configure_logging

log = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_dir)

    app = FastAPI(
        title="PitchMe",
        description="Sales pitch rehearsal: live AI buyer calls and delivery analysis",
        version=__version__,
    )

    # Browsers reject a wildcard origin together with credentials, so "*"
    # (local dev) turns credentials off. Real deployments list their origins.
    wildcard = "*" in settings.cors_origins
    if wildcard and not settings.is_dev:
        log.warning("CORS_ORIGINS is '*' outside dev; set explicit origins")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=not wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    install_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(profile.router)

    @app.get("/health", tags=["infra"])
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()

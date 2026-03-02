"""
IntelliumAI Backend — FastAPI + LM Studio
Entry point with factory pattern
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so `core`, `routers`, etc. are importable
_project_root = str(Path(__file__).resolve().parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from core.settings import settings, init_settings
from core.middleware import configure_logging, setup_middleware
from core.exceptions import ServiceError, service_error_handler

from routers import transcript, mulakat


def create_app() -> FastAPI:
    init_settings()
    configure_logging(debug=settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    setup_middleware(app, cors_origins=settings.cors_origins)

    @app.exception_handler(ServiceError)
    async def _service_error_handler(request: Request, exc: ServiceError):
        return service_error_handler(exc, instance=request.url.path)

    app.include_router(transcript.router)
    app.include_router(mulakat.router)

    @app.get("/", tags=["health"])
    async def root():
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "status": "running",
        }

    @app.get("/health", tags=["health"])
    async def health():
        from services.lm_studio_service import lm_studio_service
        lm_ok = await lm_studio_service.test_connection()
        return {
            "status": "healthy" if lm_ok else "degraded",
            "lm_studio": "connected" if lm_ok else "unreachable",
            "lm_studio_url": settings.lm_studio_url,
        }

    @app.get("/test", response_class=HTMLResponse, tags=["test"], include_in_schema=False)
    async def test_ui():
        html_path = Path(__file__).resolve().parent / "frontend_test.html"
        return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

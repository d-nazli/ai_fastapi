"""
Core middleware: RequestID, Access Logging, Security Headers, CORS
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


# ── REQUEST ID ────────────────────────────────────────────


class RequestIDMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, header_name: str = REQUEST_ID_HEADER) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers[self.header_name] = request_id
        return response


# ── ACCESS LOG ────────────────────────────────────────────


class AccessLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        request.state.request_id = request_id

        method = request.method
        path = request.url.path
        query = request.url.query
        client_ip = request.client.host if request.client else None

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": client_ip,
                },
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s %s %d %.2fms",
            method,
            path,
            f"?{query}" if query else "",
            response.status_code,
            duration_ms,
        )
        return response


# ── SECURITY HEADERS ──────────────────────────────────────


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app: FastAPI,
        enable_hsts: bool = False,
        allow_iframe_paths: Optional[Iterable[str]] = None,
    ) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.allow_iframe_paths = set(allow_iframe_paths or [])

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        path = request.url.path
        if not any(path.startswith(p) for p in self.allow_iframe_paths):
            response.headers.setdefault("X-Frame-Options", "DENY")

        if self.enable_hsts and request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )
        return response


# ── CORS SETUP ────────────────────────────────────────────


def setup_cors(app: FastAPI, origins: List[str]) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )


# ── LOGGING CONFIG ────────────────────────────────────────


def configure_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    )
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO if debug else logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("httpx").setLevel(logging.WARNING)


# ── HELPERS ───────────────────────────────────────────────


def get_request_id(request: Request) -> Optional[str]:
    return getattr(request.state, "request_id", None)


# ── ENTRYPOINT ────────────────────────────────────────────


def setup_middleware(
    app: FastAPI,
    cors_origins: Optional[List[str]] = None,
    enable_access_log: bool = True,
    enable_security_headers: bool = True,
) -> None:
    if enable_security_headers:
        app.add_middleware(SecurityHeadersMiddleware)
    if enable_access_log:
        app.add_middleware(AccessLogMiddleware)
    app.add_middleware(RequestIDMiddleware)
    setup_cors(app, cors_origins or [])

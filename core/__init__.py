"""
Core package — settings, middleware, exceptions
"""

from .settings import Settings, settings
from .db import engine, AsyncSessionLocal, get_db
from .exceptions import (
    ServiceError,
    ValidationError,
    NotFoundError,
    ExternalServiceError,
    problem_json,
    map_service_error,
    service_error_handler,
)
from .middleware import (
    configure_logging,
    setup_middleware,
    setup_cors,
    RequestIDMiddleware,
    AccessLogMiddleware,
    SecurityHeadersMiddleware,
    REQUEST_ID_HEADER,
    get_request_id,
)

__all__ = [
    "Settings",
    "settings",
    "engine",
    "get_db",
    "AsyncSessionLocal",
    "ServiceError",
    "ValidationError",
    "NotFoundError",
    "ExternalServiceError",
    "problem_json",
    "map_service_error",
    "service_error_handler",
    "configure_logging",
    "setup_middleware",
    "setup_cors",
    "RequestIDMiddleware",
    "AccessLogMiddleware",
    "SecurityHeadersMiddleware",
    "REQUEST_ID_HEADER",
    "get_request_id",
]

"""
Core exception handling — ServiceError hierarchy + RFC 7807 Problem Details
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


# ── SERVICE ERROR HIERARCHY ───────────────────────────────


class ServiceError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class ValidationError(ServiceError):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code=code, message=message, details=details, status_code=status.HTTP_400_BAD_REQUEST)


class NotFoundError(ServiceError):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code=code, message=message, details=details, status_code=status.HTTP_404_NOT_FOUND)


class ExternalServiceError(ServiceError):
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(code=code, message=message, details=details, status_code=status.HTTP_502_BAD_GATEWAY)


# ── RFC 7807 PROBLEM DETAILS ─────────────────────────────


def problem_json(
    status_code: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    instance: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    problem = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
    }
    if instance:
        problem["instance"] = instance
    if extra:
        problem.update(extra)
    return problem


# ── STATUS MAP ────────────────────────────────────────────


SERVICE_ERROR_STATUS_MAP: Dict[str, int] = {
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "INVALID_INPUT": status.HTTP_400_BAD_REQUEST,
    "FILE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "AI_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
    "EXTERNAL_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
    "WEBHOOK_ERROR": status.HTTP_502_BAD_GATEWAY,
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "PARSE_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
}


def _resolve_status_code(error: ServiceError) -> int:
    if error.status_code is not None:
        return error.status_code
    return SERVICE_ERROR_STATUS_MAP.get(error.code, status.HTTP_500_INTERNAL_SERVER_ERROR)


# ── ERROR → RESPONSE ─────────────────────────────────────


def map_service_error(error: ServiceError, instance: Optional[str] = None) -> HTTPException:
    http_status = _resolve_status_code(error)
    title_map = {
        400: "Bad Request",
        404: "Not Found",
        422: "Unprocessable Entity",
        500: "Internal Server Error",
        502: "Bad Gateway",
    }
    problem_details = problem_json(
        status_code=http_status,
        title=title_map.get(http_status, "Error"),
        detail=error.message,
        type_uri=f"https://httpstatuses.com/{http_status}",
        instance=instance,
        extra={"code": error.code, **(error.details or {})},
    )
    return HTTPException(
        status_code=http_status,
        detail=problem_details,
        headers={"Content-Type": "application/problem+json"},
    )


def service_error_handler(error: ServiceError, instance: Optional[str] = None) -> JSONResponse:
    http_exc = map_service_error(error, instance=instance)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
        headers={"Content-Type": "application/problem+json"},
    )

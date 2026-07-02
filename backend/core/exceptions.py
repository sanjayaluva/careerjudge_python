"""Custom DRF exception handler that returns a consistent error envelope."""

import logging

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_default_handler

logger = logging.getLogger(__name__)


def _format_details(data) -> str:
    """Extract a human-readable message from DRF error details."""
    parts: list[str] = []
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                msgs = [str(v) for v in value]
                parts.append(f"{key}: {', '.join(msgs)}")
            elif isinstance(value, str):
                parts.append(f"{key}: {value}")
            else:
                parts.append(f"{key}: {value}")
    elif isinstance(data, list):
        for item in data:
            parts.append(str(item))
    return "; ".join(parts) if parts else ""


def exception_handler(exc, context):
    response = drf_default_handler(exc, context)
    if response is None:
        # Unhandled 500 — log the full exception and return a clean envelope
        logger.exception("Unhandled exception in view: %s", exc)
        return Response(
            {
                "error": {
                    "code": "server_error",
                    "message": "An unexpected error occurred.",
                    "details": {},
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Determine error code from exception type
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        code = "unauthorized" if response.status_code == 401 else "forbidden"
    elif isinstance(exc, PermissionDenied):
        code = "forbidden"
    else:
        code = "error"

    # Normalize the response body to { error: { code, message, details } }
    data = response.data
    if isinstance(data, dict) and "error" in data:
        return response  # already normalized

    if isinstance(data, dict):
        # Check if it's a DRF ValidationError detail dict
        # (field → list of ErrorDetail, or field → ErrorDetail string)
        has_list_values = any(isinstance(v, (list, tuple)) for v in data.values())

        if (
            has_list_values
            or any(isinstance(v, str) for v in data.values() if not isinstance(v, (list, tuple)))
            and "detail" not in data
        ):
            # Field validation errors: { "email": ["This field is required."] }
            msg = _format_details(data) or "Validation failed."
            response.data = {
                "error": {
                    "code": "validation_error",
                    "message": msg,
                    "details": data,
                }
            }
        elif "detail" in data:
            # DRF-style error with a detail message
            detail = data["detail"]
            detail_code = getattr(detail, "code", code) if hasattr(detail, "code") else code
            response.data = {
                "error": {
                    "code": detail_code,
                    "message": str(detail) if str(detail) else "Error.",
                    "details": {},
                }
            }
        else:
            # Unknown dict structure — try to extract a readable message
            msg = _format_details(data) or str(data) or "Error."
            response.data = {
                "error": {
                    "code": code,
                    "message": msg,
                    "details": data,
                }
            }
    elif isinstance(data, list):
        msg = _format_details(data) or "Validation failed."
        response.data = {
            "error": {
                "code": "validation_error",
                "message": msg,
                "details": {"non_field_errors": data},
            }
        }
    else:
        response.data = {
            "error": {
                "code": code,
                "message": str(data) if data else "Error.",
                "details": {},
            }
        }

    return response

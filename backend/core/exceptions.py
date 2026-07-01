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
        # Field validation errors: { "email": ["This field is required."] }
        if any(isinstance(v, list) for v in data.values()):
            response.data = {
                "error": {
                    "code": "validation_error",
                    "message": "Validation failed.",
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
            # Unknown dict structure — include the raw data in details for debugging
            logger.warning("Unhandled error response structure: %s", data)
            response.data = {
                "error": {
                    "code": code,
                    "message": str(data) if data else "Error.",
                    "details": data,
                }
            }
    elif isinstance(data, list):
        response.data = {
            "error": {
                "code": "validation_error",
                "message": "Validation failed.",
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

"""Custom DRF exception handler that returns a consistent error envelope."""
from rest_framework.views import exception_handler as drf_default_handler
from rest_framework.response import Response
from rest_framework import status


def exception_handler(exc, context):
    response = drf_default_handler(exc, context)
    if response is None:
        # Unhandled 500 — return a clean envelope
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
        else:
            response.data = {
                "error": {
                    "code": data.get("code", "error"),
                    "message": data.get("detail", "Error."),
                    "details": {},
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
                "code": "error",
                "message": str(data),
                "details": {},
            }
        }

    return response

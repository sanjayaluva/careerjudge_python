"""Images uploaded from the shared rich-text editor (Signed Doc 3 §2.1.2
"Image Upload").

The editor used to insert images by URL only. An author now picks a file from
his computer; it is stored under ``editor_images/`` with a random name and the
editor inserts the returned ``/api/uploads/editor-images/<name>`` URL.

Files are served through the API (like the corporate logo, Report 9 #49)
because the deploy proxy forwards only ``/api/*`` to the backend — media URLs
are not reachable. Serving is public: the HTML is shown to candidates,
students and site visitors, and ``<img>`` requests carry no token. The names
are random 128-bit hex, so they cannot be guessed or listed.
"""

import mimetypes
import uuid

from django.core.files.storage import default_storage
from django.http import FileResponse
from PIL import Image, UnidentifiedImageError
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

EDITOR_IMAGE_DIR = "editor_images"
EDITOR_IMAGE_MAX_BYTES = 5 * 1024 * 1024
# Pillow format → stored extension. No SVG: it can carry script.
EDITOR_IMAGE_FORMATS = {"PNG": "png", "JPEG": "jpg", "GIF": "gif", "WEBP": "webp"}


def _error(message: str, code: str = "validation_error"):
    return Response(
        {"error": {"code": code, "message": message, "details": {}}},
        status=status.HTTP_400_BAD_REQUEST,
    )


class EditorImageUploadView(APIView):
    """POST /api/uploads/editor-images/  (multipart field ``image``)

    Any signed-in user (the editor is used by every authoring role). Only
    PNG / JPEG / GIF / WebP up to 5 MB; the content is checked, not just the
    file name."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        upload = request.FILES.get("image")
        if upload is None:
            return _error("Choose an image file to upload.")
        if upload.size > EDITOR_IMAGE_MAX_BYTES:
            return _error("The image is larger than 5 MB.")
        try:
            with Image.open(upload) as img:
                fmt = img.format
                img.verify()
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError):
            return _error("This file is not a valid image.")
        ext = EDITOR_IMAGE_FORMATS.get(fmt or "")
        if ext is None:
            return _error("Upload a PNG, JPEG, GIF or WebP image.")
        upload.seek(0)
        name = default_storage.save(f"{EDITOR_IMAGE_DIR}/{uuid.uuid4().hex}.{ext}", upload)
        filename = name.rsplit("/", 1)[-1]
        return Response(
            {
                "message": "Image uploaded.",
                "data": {"url": f"/api/uploads/editor-images/{filename}"},
            },
            status=status.HTTP_201_CREATED,
        )


class EditorImageView(APIView):
    """GET /api/uploads/editor-images/<name>  — public, see the module note."""

    permission_classes = [AllowAny]
    # A stale token in the viewer's browser must not turn this into a 401.
    authentication_classes = []

    def get(self, request, filename):
        path = f"{EDITOR_IMAGE_DIR}/{filename}"
        try:
            handle = default_storage.open(path, "rb")
        except (FileNotFoundError, OSError) as exc:
            raise NotFound("Image not found.") from exc
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        response = FileResponse(handle, content_type=content_type)
        # Random, never-reused names: the file never changes.
        response["Cache-Control"] = "public, max-age=31536000, immutable"
        response["X-Content-Type-Options"] = "nosniff"
        return response

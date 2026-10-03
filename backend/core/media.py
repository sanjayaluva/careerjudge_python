"""Signed, time-limited URLs for uploaded files on local disk (code review,
3 Oct 2026).

Uploaded files — paid course videos and documents, learners' assignment
reports, avatars, report images — used to be served to anyone at
``/media/<path>``, and the paths keep the original file names, so they could
be guessed. Every URL the storage hands out (``FieldFile.url``, hence every
serializer's file field) now carries an expiry and a signature over the path,
and ``/media/<path>`` serves the file only for a valid, unexpired signature.

The expiry is rounded to the hour so a file keeps the same URL for an hour
(browsers can cache avatars and resume videos) and stays valid for 12-13 h —
longer than a sitting with the page open. Range requests are honoured so
browsers can seek in audio and video (Django's static ``serve`` ignores them).

The public corporate logo (``/api/organizations/site/<slug>/logo/``) and the
editor images (``/api/uploads/editor-images/<name>``) keep their own public
endpoints.
"""

import mimetypes
import os
import re
import time
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.storage import FileSystemStorage, default_storage
from django.core.signing import Signer
from django.http import FileResponse, Http404, HttpResponse, StreamingHttpResponse
from django.utils.crypto import constant_time_compare
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_safe

_SALT = "core.media.signed-url"
_HOUR = 60 * 60
# Types a browser may show inline; anything else (HTML, SVG, XML, Office
# files, …) is sent as a download so an upload can never run script on the
# application's origin.
_INLINE_PREFIXES = ("image/png", "image/jpeg", "image/gif", "image/webp", "video/", "audio/")
_INLINE_TYPES = ("application/pdf",)
_RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")
_CHUNK = 64 * 1024


def _max_age() -> int:
    return int(getattr(settings, "MEDIA_URL_MAX_AGE", 12 * _HOUR))


def _normalize(name: str) -> str:
    return str(name).replace("\\", "/").lstrip("/")


def media_signature(name: str, expires: int) -> str:
    return Signer(salt=_SALT).signature(f"{_normalize(name)}:{int(expires)}")


def media_expiry(now: float | None = None) -> int:
    """Expiry for a URL issued now: at least ``MEDIA_URL_MAX_AGE`` ahead,
    rounded up to the hour so the URL is stable for that hour."""
    now = int(time.time() if now is None else now)
    return (now + _max_age()) // _HOUR * _HOUR + _HOUR


def signed_query(name: str, now: float | None = None) -> str:
    expires = media_expiry(now)
    return urlencode({"exp": expires, "sig": media_signature(name, expires)})


def media_signature_valid(name: str, expires, signature, now: float | None = None) -> bool:
    try:
        expires = int(expires)
    except (TypeError, ValueError):
        return False
    if not signature or expires < (time.time() if now is None else now):
        return False
    return constant_time_compare(str(signature), media_signature(name, expires))


class SignedMediaStorage(FileSystemStorage):
    """Local-disk storage whose URLs are signed and expire (see module note)."""

    def url(self, name):
        url = super().url(name)
        if name is None:
            return url
        return f"{url}?{signed_query(name)}"


def _byte_range(header: str | None, size: int):
    """``(start, end)`` for a single ``bytes=`` range, ``None`` to send the
    whole file (no/unsupported header), or ``False`` if unsatisfiable."""
    match = _RANGE_RE.match((header or "").strip())
    if match is None:
        return None
    first, last = match.groups()
    if not first and not last:
        return None
    if size == 0:  # nothing to slice: any range is unsatisfiable (416)
        return False
    if not first:  # suffix range: the last N bytes
        length = int(last)
        if length == 0:
            return False
        return max(size - length, 0), size - 1
    start = int(first)
    end = min(int(last), size - 1) if last else size - 1
    if start >= size or end < start:
        return False
    return start, end


def _read(handle, length):
    try:
        while length > 0:
            chunk = handle.read(min(_CHUNK, length))
            if not chunk:
                break
            length -= len(chunk)
            yield chunk
    finally:
        handle.close()


@require_safe
def serve_signed_media(request, path):
    """GET /media/<path>?exp=…&sig=… — the file, for a valid signature only."""
    if not media_signature_valid(path, request.GET.get("exp"), request.GET.get("sig")):
        return HttpResponse(
            "This file link is invalid or has expired. Reload the page to get a new one.",
            status=403,
            content_type="text/plain; charset=utf-8",
        )
    try:
        full_path = default_storage.path(path)
    except (SuspiciousFileOperation, NotImplementedError) as exc:
        raise Http404("File not found.") from exc
    if not os.path.isfile(full_path):
        raise Http404("File not found.")

    size = os.path.getsize(full_path)
    content_type = mimetypes.guess_type(full_path)[0] or "application/octet-stream"
    inline = content_type.startswith(_INLINE_PREFIXES) or content_type in _INLINE_TYPES
    byte_range = _byte_range(request.headers.get("Range"), size)
    if byte_range is False:
        response = HttpResponse(status=416)
        response["Content-Range"] = f"bytes */{size}"
        return response
    if byte_range is None:
        response = FileResponse(
            open(full_path, "rb"),  # noqa: SIM115 — closed by FileResponse
            content_type=content_type,
            as_attachment=not inline,
        )
    else:
        start, end = byte_range
        handle = open(full_path, "rb")  # noqa: SIM115 — closed by _read
        handle.seek(start)
        response = StreamingHttpResponse(
            _read(handle, end - start + 1), status=206, content_type=content_type
        )
        response["Content-Length"] = str(end - start + 1)
        response["Content-Range"] = f"bytes {start}-{end}/{size}"
        disposition = content_disposition_header(not inline, os.path.basename(full_path))
        if disposition:
            response["Content-Disposition"] = disposition
    response["Accept-Ranges"] = "bytes"
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=3600"
    return response

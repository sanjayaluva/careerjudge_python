"""Signed Doc 3 §2.1.2 "Image Upload": the shared rich-text editor uploads an
image from the author's computer (core.uploads) and inserts the returned
``/api/uploads/editor-images/<name>`` URL, which the stored-HTML sanitiser
keeps. Lives here because CI collects tests under ``apps/`` only."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from apps.accounts.tests.factories import UserFactory
from core.rich_html import sanitize_rich_html
from core.uploads import EDITOR_IMAGE_MAX_BYTES

pytestmark = pytest.mark.django_db

URL = "/api/uploads/editor-images/"


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    return tmp_path


def _png(name="photo.png", fmt="PNG", content_type="image/png"):
    buf = io.BytesIO()
    Image.new("RGB", (4, 4), (200, 10, 10)).save(buf, fmt)
    return SimpleUploadedFile(name, buf.getvalue(), content_type=content_type)


def _client(user=None):
    c = APIClient()
    if user is not None:
        c.force_authenticate(user)
    return c


def test_signed_in_user_uploads_and_anyone_can_view(media_root):
    resp = _client(UserFactory()).post(URL, {"image": _png()}, format="multipart")
    assert resp.status_code == 201, resp.data
    url = resp.data["data"]["url"]
    assert url.startswith("/api/uploads/editor-images/") and url.endswith(".png")
    assert len(list((media_root / "editor_images").iterdir())) == 1

    # Served through /api/* with no token (the <img> tag sends none).
    shown = _client().get(url)
    assert shown.status_code == 200
    assert shown["Content-Type"] == "image/png"
    assert shown["X-Content-Type-Options"] == "nosniff"
    assert b"".join(shown.streaming_content).startswith(b"\x89PNG")


def test_jpeg_is_stored_by_its_real_format():
    upload = _png("holiday.png", fmt="JPEG", content_type="image/png")
    resp = _client(UserFactory()).post(URL, {"image": upload}, format="multipart")
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["url"].endswith(".jpg")


def test_anonymous_upload_refused():
    assert _client().post(URL, {"image": _png()}, format="multipart").status_code == 401


def test_non_images_and_svg_refused(media_root):
    c = _client(UserFactory())
    fake = SimpleUploadedFile("x.png", b"<script>alert(1)</script>", content_type="image/png")
    assert c.post(URL, {"image": fake}, format="multipart").status_code == 400
    svg = SimpleUploadedFile(
        "x.svg", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>', content_type="image/svg+xml"
    )
    assert c.post(URL, {"image": svg}, format="multipart").status_code == 400
    assert c.post(URL, {}, format="multipart").status_code == 400
    assert not (media_root / "editor_images").exists()


def test_bmp_format_refused():
    upload = _png("x.bmp", fmt="BMP", content_type="image/bmp")
    resp = _client(UserFactory()).post(URL, {"image": upload}, format="multipart")
    assert resp.status_code == 400


def test_over_5_mb_refused():
    big = SimpleUploadedFile(
        "big.png", b"\x89PNG" + b"0" * EDITOR_IMAGE_MAX_BYTES, content_type="image/png"
    )
    resp = _client(UserFactory()).post(URL, {"image": big}, format="multipart")
    assert resp.status_code == 400
    assert "5 MB" in resp.data["error"]["message"]


def test_unknown_image_is_404():
    missing = "/api/uploads/editor-images/" + "0" * 32 + ".png"
    assert _client().get(missing).status_code == 404
    # Only random hex names are routed — no path tricks.
    assert _client().get("/api/uploads/editor-images/../settings.py").status_code == 404


def test_sanitiser_keeps_uploaded_image_src():
    url = "/api/uploads/editor-images/" + "a" * 32 + ".png"
    out = sanitize_rich_html(f'<p>See</p><img src="{url}" alt="chart">')
    assert f'src="{url}"' in out

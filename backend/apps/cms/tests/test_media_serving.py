"""Uploaded media are served by Django without DEBUG (deployment review) —
only through signed, expiring URLs (code review, 3 Oct 2026, core.media)."""

import time
from urllib.parse import parse_qs, urlsplit

import pytest
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User
from core.media import media_signature

pytestmark = pytest.mark.django_db

PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00"
    b"\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
    b"\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


def _body(resp):
    if getattr(resp, "streaming", False):
        return b"".join(resp.streaming_content)
    return resp.content


def _path_and_query(url):
    parts = urlsplit(url)
    return parts.path, {k: v[0] for k, v in parse_qs(parts.query).items()}


def test_uploaded_media_is_served_even_without_debug(client):
    """Uploaded files (training media, avatars, logos) must be reachable when
    DEBUG is off — they used to 404 (Report 9 deployment review)."""
    from django.conf import settings as dj_settings

    assert not dj_settings.DEBUG
    name = default_storage.save("session_media/lesson 1.txt", ContentFile(b"ok"))
    url = default_storage.url(name)
    assert "sig=" in url and "exp=" in url
    resp = client.get(url)
    assert resp.status_code == 200
    assert _body(resp) == b"ok"
    assert resp["X-Content-Type-Options"] == "nosniff"


def test_unsigned_media_url_is_refused(client):
    name = default_storage.save("session_media/paid.mp4", ContentFile(b"video"))
    assert client.get(f"/media/{name}").status_code == 403


def test_tampered_media_url_is_refused(client):
    a = default_storage.save("session_documents/a.pdf", ContentFile(b"A"))
    b = default_storage.save("session_documents/b.pdf", ContentFile(b"B"))
    path, query = _path_and_query(default_storage.url(a))
    # Another file with a's signature, a's file with a changed signature or
    # a pushed-out expiry: all refused.
    assert client.get(f"/media/{b}", query).status_code == 403
    assert client.get(path, {**query, "sig": query["sig"][:-2] + "xx"}).status_code == 403
    assert client.get(path, {**query, "exp": int(query["exp"]) + 3600}).status_code == 403
    assert client.get(path, query).status_code == 200


def test_expired_media_url_is_refused(client):
    name = default_storage.save("assignment_reports/r.pdf", ContentFile(b"R"))
    expired = int(time.time()) - 10
    resp = client.get(f"/media/{name}", {"exp": expired, "sig": media_signature(name, expired)})
    assert resp.status_code == 403


def test_url_lasts_at_least_twelve_hours_and_is_stable(client):
    name = default_storage.save("avatars/a.png", ContentFile(PNG))
    url = default_storage.url(name)
    _, query = _path_and_query(url)
    assert int(query["exp"]) >= time.time() + 12 * 3600 - 5
    assert default_storage.url(name) == url  # cacheable within the hour


def test_missing_file_and_traversal_are_404(client):
    missing = "avatars/none.png"
    exp = int(time.time()) + 3600
    resp = client.get(f"/media/{missing}", {"exp": exp, "sig": media_signature(missing, exp)})
    assert resp.status_code == 404
    evil = "../config/settings/base.py"
    resp = client.get(f"/media/{evil}", {"exp": exp, "sig": media_signature(evil, exp)})
    assert resp.status_code in (403, 404)


def test_range_requests_for_seeking(client):
    name = default_storage.save("session_media/clip.mp4", ContentFile(b"0123456789"))
    url = default_storage.url(name)
    resp = client.get(url, HTTP_RANGE="bytes=2-5")
    assert resp.status_code == 206
    assert _body(resp) == b"2345"
    assert resp["Content-Range"] == "bytes 2-5/10"
    assert resp["Accept-Ranges"] == "bytes"
    resp = client.get(url, HTTP_RANGE="bytes=7-")
    assert resp.status_code == 206 and _body(resp) == b"789"
    resp = client.get(url, HTTP_RANGE="bytes=-3")
    assert resp.status_code == 206 and _body(resp) == b"789"
    resp = client.get(url, HTTP_RANGE="bytes=50-")
    assert resp.status_code == 416


def test_active_content_is_downloaded_not_rendered(client):
    name = default_storage.save("session_documents/page.html", ContentFile(b"<script>x</script>"))
    resp = client.get(default_storage.url(name))
    assert resp.status_code == 200
    assert resp["Content-Disposition"].startswith("attachment")


def test_avatar_url_from_the_api_is_signed_and_works(client):
    user = User.objects.create_user(email="me@t.com", password="pw", is_active=True)
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    resp = api.post(
        "/api/me/avatar",
        {"avatar": SimpleUploadedFile("me.png", PNG, "image/png")},
        format="multipart",
    )
    assert resp.status_code == 200, resp.data
    url = resp.data["data"]["avatar"]
    assert "sig=" in url
    me = api.get("/api/me/").data["data"]
    assert "sig=" in me["profile"]["avatar"]
    path, query = _path_and_query(url)
    fetched = client.get(path, query)
    assert fetched.status_code == 200
    assert _body(fetched) == PNG
    assert client.get(path).status_code == 403


def test_absolute_media_links_use_https_behind_the_proxy(
    client, django_user_model, tmp_path, settings
):
    """Behind Caddy (X-Forwarded-Proto: https) the avatar upload returns an
    https link, not http (which the https site would block or redirect)."""
    import base64

    from django.core.files.uploadedfile import SimpleUploadedFile

    from apps.accounts.models import Role

    settings.MEDIA_ROOT = tmp_path
    role, _ = Role.objects.get_or_create(name="individual", defaults={"is_system": True})
    user = django_user_model.objects.create_user(
        email="https@t.com", password="pw", is_active=True, role=role
    )
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=user)
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    )
    resp = client.post(
        "/api/me/avatar",
        {"avatar": SimpleUploadedFile("a.png", png, content_type="image/png")},
        format="multipart",
        HTTP_X_FORWARDED_PROTO="https",
    )
    assert resp.status_code in (200, 201), resp.content
    assert "http://" not in resp.content.decode()
    assert "https://" in resp.content.decode()

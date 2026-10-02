"""Uploaded media are served by Django without DEBUG (deployment review)."""

import pytest

pytestmark = pytest.mark.django_db


def test_uploaded_media_is_served_even_without_debug(client):
    """Uploaded files (training media, avatars, logos) must be reachable when
    DEBUG is off — they used to 404 (Report 9 deployment review)."""
    import uuid
    from pathlib import Path

    from django.conf import settings as dj_settings

    assert not dj_settings.DEBUG
    folder = Path(dj_settings.MEDIA_ROOT) / "test-media-check"
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.txt"
    (folder / name).write_text("ok")
    try:
        resp = client.get(f"/media/test-media-check/{name}")
        assert resp.status_code == 200
        assert b"".join(resp.streaming_content) == b"ok"
    finally:
        (folder / name).unlink()
        folder.rmdir()

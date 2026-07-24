"""Zoom API integration — optional auto-create meetings.

Uses Zoom Server-to-Server OAuth app credentials (env vars):
  ZOOM_ACCOUNT_ID
  ZOOM_CLIENT_ID
  ZOOM_CLIENT_SECRET

If these are not set, Zoom is 'not configured' and the UI falls back
to manual URL entry (the default behavior).
"""

import logging
import os

logger = logging.getLogger(__name__)


def is_zoom_configured() -> bool:
    """Check if Zoom API credentials are configured."""
    return bool(
        os.environ.get("ZOOM_ACCOUNT_ID")
        and os.environ.get("ZOOM_CLIENT_ID")
        and os.environ.get("ZOOM_CLIENT_SECRET")
    )


def create_zoom_meeting(topic: str, start_time: str, duration_minutes: int = 60) -> dict | None:
    """Create a Zoom meeting via the API.

    Args:
        topic: Meeting title
        start_time: ISO 8601 datetime string (e.g., "2026-08-01T10:00:00Z")
        duration_minutes: Meeting duration

    Returns:
        Dict with 'join_url', 'meeting_id', 'password' on success.
        None if Zoom is not configured or the API call fails.
    """
    if not is_zoom_configured():
        return None

    try:
        import requests

        # Step 1: Get access token via Server-to-Server OAuth
        token_resp = requests.post(
            "https://zoom.us/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "account_credentials",
                "account_id": os.environ["ZOOM_ACCOUNT_ID"],
            },
            auth=(os.environ["ZOOM_CLIENT_ID"], os.environ["ZOOM_CLIENT_SECRET"]),
            timeout=10,
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        # Step 2: Create meeting
        meeting_resp = requests.post(
            "https://api.zoom.us/v2/users/me/meetings",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            json={
                "topic": topic,
                "type": 2,  # Scheduled meeting
                "start_time": start_time,
                "duration": duration_minutes,
                "settings": {
                    "join_before_host": False,
                    "waiting_room": True,
                },
            },
            timeout=10,
        )
        meeting_resp.raise_for_status()
        data = meeting_resp.json()

        return {
            "join_url": data.get("join_url", ""),
            "meeting_id": data.get("id", ""),
            "password": data.get("password", ""),
        }
    except Exception as e:
        logger.error("Zoom meeting creation failed: %s", e)
        return None

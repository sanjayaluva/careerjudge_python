"""Tests for the CMS module."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight
from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.cms.models import Banner, MenuItem, Page

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


@pytest.fixture
def admin_user(db, roles):
    role = roles["cj_admin"]
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=role, module="cms", action=action)
    return UserFactory(role=role, email="admin@cms.test")


@pytest.fixture
def admin_client(db, admin_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    c = APIClient()
    refresh = RefreshToken.for_user(admin_user)
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return c


# ---------------------------------------------------------------------------
# Page tests
# ---------------------------------------------------------------------------


def test_admin_can_create_page(admin_client):
    resp = admin_client.post(
        "/api/cms/pages/",
        {"title": "About Us", "slug": "about", "body": "<p>Content here</p>"},
        format="json",
    )
    assert resp.status_code == 201, f"Got {resp.status_code}: {resp.data}"
    assert resp.data["data"]["slug"] == "about"


def test_list_pages(admin_client):
    Page.objects.create(title="About", slug="about", body="x", status="published")
    Page.objects.create(title="Privacy", slug="privacy", body="x", status="draft")
    resp = admin_client.get("/api/cms/pages/")
    assert resp.status_code == 200
    data = resp.data["data"]
    results = data["results"] if isinstance(data, dict) and "results" in data else data
    assert len(results) == 2


def test_retrieve_page_by_slug(admin_client):
    Page.objects.create(title="Terms", slug="terms", body="<p>Terms</p>", status="published")
    resp = admin_client.get("/api/cms/pages/slug/terms/")
    assert resp.status_code == 200
    assert resp.data["data"]["title"] == "Terms"


def test_draft_page_not_visible_by_slug(admin_client):
    Page.objects.create(title="Draft", slug="draft", body="x", status="draft")
    resp = admin_client.get("/api/cms/pages/slug/draft/")
    assert resp.status_code == 404


def test_update_page(admin_client):
    page = Page.objects.create(title="Old", slug="old", body="old")
    resp = admin_client.patch(
        f"/api/cms/pages/{page.id}/",
        {"title": "New Title"},
        format="json",
    )
    assert resp.status_code == 200
    page.refresh_from_db()
    assert page.title == "New Title"


def test_delete_page(admin_client):
    page = Page.objects.create(title="Del", slug="del", body="x")
    resp = admin_client.delete(f"/api/cms/pages/{page.id}/")
    assert resp.status_code == 204
    assert not Page.objects.filter(id=page.id).exists()


# ---------------------------------------------------------------------------
# Banner tests
# ---------------------------------------------------------------------------


def test_create_banner(admin_client):
    resp = admin_client.post(
        "/api/cms/banners/",
        {"title": "Summer Sale", "subtitle": "50% off", "position": "hero"},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["position"] == "hero"


def test_list_banners_filter_by_position(admin_client):
    Banner.objects.create(title="Hero", position="hero")
    Banner.objects.create(title="Footer", position="footer")
    resp = admin_client.get("/api/cms/banners/?position=hero")
    assert resp.status_code == 200
    data = resp.data["data"]
    results = data["results"] if isinstance(data, dict) and "results" in data else data
    assert len(results) == 1
    assert results[0]["title"] == "Hero"


def test_toggle_banner_active(admin_client):
    banner = Banner.objects.create(title="Test", position="hero", is_active=True)
    resp = admin_client.patch(
        f"/api/cms/banners/{banner.id}/",
        {"is_active": False},
        format="json",
    )
    assert resp.status_code == 200
    banner.refresh_from_db()
    assert banner.is_active is False


# ---------------------------------------------------------------------------
# Menu item tests
# ---------------------------------------------------------------------------


def test_create_menu_item(admin_client):
    resp = admin_client.post(
        "/api/cms/menu/",
        {"label": "Home", "url": "/", "location": "header", "order": 1},
        format="json",
    )
    assert resp.status_code == 201
    assert resp.data["data"]["label"] == "Home"


def test_list_menu_items_by_location(admin_client):
    MenuItem.objects.create(label="Home", url="/", location="header", order=1)
    MenuItem.objects.create(label="Privacy", url="/privacy", location="footer", order=1)
    resp = admin_client.get("/api/cms/menu/?location=footer")
    assert resp.status_code == 200
    data = resp.data["data"]
    results = data["results"] if isinstance(data, dict) and "results" in data else data
    assert len(results) == 1
    assert results[0]["label"] == "Privacy"

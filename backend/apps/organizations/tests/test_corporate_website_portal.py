"""Report 9 #48/#49/#51/#52/#95 — the corporate branded portal (CJ_UC054/UC055).

The logo is a real upload (validated, served through the public API), the
company name stays editable, the public branding endpoint feeds the
/site/<slug> page, and a member's own portal branding is available to the app.
"""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.organizations.models import CorporateWebsite, Organization, OrganizationMember

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


@pytest.fixture
def roles(db):
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _auth(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


def _user(roles, role, email):
    return User.objects.create_user(email=email, password="pw", is_active=True, role=roles[role])


def _png(name="logo.png", size=(4, 4)):
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buf, format="PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@pytest.fixture
def world(roles):
    org = Organization.objects.create(name="Exclusive Co", type="corp_exclusive")
    cj = _user(roles, "cj_admin", "cj@t.com")
    admin = _user(roles, "corp_exclusive", "excl@t.com")
    OrganizationMember.objects.create(organization=org, user=admin, is_admin=True)
    emp = _user(roles, "individual", "emp@t.com")
    OrganizationMember.objects.create(organization=org, user=emp)
    outsider = _user(roles, "individual", "out@t.com")
    resp = _auth(cj).post(
        f"/api/organizations/{org.id}/website/",
        {"company_name": "Exclusive Co", "layout": "modern"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    return {"org": org, "cj": cj, "admin": admin, "emp": emp, "outsider": outsider}


def _url(world):
    return f"/api/organizations/{world['org'].id}/website/"


# --- #49: logo upload ----------------------------------------------------


def test_org_admin_uploads_logo_and_public_site_returns_it(world):
    resp = _auth(world["admin"]).patch(_url(world), {"logo": _png()}, format="multipart")
    assert resp.status_code == 200, resp.data
    website = CorporateWebsite.objects.get(organization=world["org"])
    assert website.logo.name.startswith("corporate_logos/")
    src = resp.data["data"]["logo_src"]
    assert src.startswith(f"/api/organizations/site/{website.slug}/logo/")
    assert "logo" not in resp.data["data"]  # write-only

    public = APIClient().get(f"/api/organizations/site/{website.slug}/")
    assert public.status_code == 200
    assert public.data["data"]["logo_url"] == src

    image = APIClient().get(f"/api/organizations/site/{website.slug}/logo/")
    assert image.status_code == 200
    assert image["Content-Type"] == "image/png"
    assert b"".join(image.streaming_content).startswith(b"\x89PNG")


def test_logo_upload_rejects_non_images(world):
    fake = SimpleUploadedFile("logo.png", b"not really an image", content_type="image/png")
    resp = _auth(world["admin"]).patch(_url(world), {"logo": fake}, format="multipart")
    assert resp.status_code == 400
    svg = SimpleUploadedFile("logo.svg", b"<svg onload='alert(1)'/>", content_type="image/svg+xml")
    resp = _auth(world["admin"]).patch(_url(world), {"logo": svg}, format="multipart")
    assert resp.status_code == 400
    assert not CorporateWebsite.objects.get(organization=world["org"]).logo


def test_logo_upload_rejects_large_files(world, monkeypatch):
    from apps.organizations import serializers as org_serializers

    monkeypatch.setattr(org_serializers, "LOGO_MAX_BYTES", 10)
    resp = _auth(world["admin"]).patch(_url(world), {"logo": _png()}, format="multipart")
    assert resp.status_code == 400
    assert "2 MB" in str(resp.data)


def test_typed_logo_url_still_accepted_and_replaces_upload(world):
    c = _auth(world["admin"])
    assert c.patch(_url(world), {"logo": _png()}, format="multipart").status_code == 200
    resp = c.patch(_url(world), {"logo_url": "https://cdn.example.com/x.png"}, format="json")
    assert resp.status_code == 200, resp.data
    website = CorporateWebsite.objects.get(organization=world["org"])
    assert not website.logo
    assert resp.data["data"]["logo_src"] == "https://cdn.example.com/x.png"
    public = APIClient().get(f"/api/organizations/site/{website.slug}/")
    assert public.data["data"]["logo_url"] == "https://cdn.example.com/x.png"


def test_logo_endpoint_404_without_upload(world):
    slug = CorporateWebsite.objects.get(organization=world["org"]).slug
    assert APIClient().get(f"/api/organizations/site/{slug}/logo/").status_code == 404


def test_create_website_with_uploaded_logo(roles):
    org = Organization.objects.create(name="Logo Corp", type="corporate")
    cj = _user(roles, "cj_admin", "cj2@t.com")
    resp = _auth(cj).post(
        f"/api/organizations/{org.id}/website/",
        {"company_name": "Logo Corp", "layout": "minimal", "logo": _png()},
        format="multipart",
    )
    assert resp.status_code == 201, resp.data
    assert CorporateWebsite.objects.get(organization=org).logo
    assert resp.data["data"]["logo_src"].startswith("/api/organizations/site/logo-corp/logo/")


# --- #49: company name editable (CJ_UC054 'Editable: Y') ------------------


def test_company_name_editable_after_creation(world):
    c = _auth(world["admin"])
    website = CorporateWebsite.objects.get(organization=world["org"])
    resp = c.patch(_url(world), {"company_name": "Exclusive Company Ltd"}, format="json")
    assert resp.status_code == 200, resp.data
    assert resp.data["data"]["company_name"] == "Exclusive Company Ltd"
    # The portal address stays the same so links already shared keep working.
    assert resp.data["data"]["slug"] == website.slug
    public = APIClient().get(f"/api/organizations/site/{website.slug}/")
    assert public.data["data"]["company_name"] == "Exclusive Company Ltd"


def test_blank_company_name_and_bad_values_rejected(world):
    c = _auth(world["admin"])
    assert c.patch(_url(world), {"company_name": "  "}, format="json").status_code == 400
    assert c.patch(_url(world), {"layout": "fancy"}, format="json").status_code == 400
    assert c.patch(_url(world), {"primary_color": "red;"}, format="json").status_code == 400


def test_outsider_cannot_customize(world):
    resp = _auth(world["outsider"]).patch(_url(world), {"company_name": "Hacked"}, format="json")
    assert resp.status_code in (403, 404)
    assert CorporateWebsite.objects.get(organization=world["org"]).company_name == "Exclusive Co"


# --- #48/#95: public portal ----------------------------------------------


def test_public_site_ignores_stale_token(world):
    slug = CorporateWebsite.objects.get(organization=world["org"]).slug
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Bearer not-a-valid-token")
    resp = c.get(f"/api/organizations/site/{slug}/")
    assert resp.status_code == 200
    assert resp.data["data"]["layout"] == "modern"


def test_inactive_site_not_public(world):
    _auth(world["cj"]).patch(_url(world), {"is_active": False}, format="json")
    slug = CorporateWebsite.objects.get(organization=world["org"]).slug
    assert APIClient().get(f"/api/organizations/site/{slug}/").status_code == 404


# --- #51/#52: member's own portal branding --------------------------------


def test_member_gets_own_portal_branding(world):
    resp = _auth(world["emp"]).get("/api/organizations/my-site/")
    assert resp.status_code == 200
    assert resp.data["data"]["company_name"] == "Exclusive Co"
    assert resp.data["data"]["organization_id"] == world["org"].id


def test_non_member_gets_no_portal_branding(world):
    resp = _auth(world["outsider"]).get("/api/organizations/my-site/")
    assert resp.status_code == 200
    assert resp.data["data"] is None
    assert APIClient().get("/api/organizations/my-site/").status_code == 401

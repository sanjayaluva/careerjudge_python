"""Corporate-Exclusive Phase 2 + 3.

Phase 2: WP-D schedule assessment + notify (CJ_UC053), WP-G corporate report
scoping (Doc 4). Phase 3: WP-E customize page + WP-F create website
(CJ_UC054/UC055) — logical multi-tenancy.
"""

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import ModuleRight, User
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment, AssessmentSession
from apps.notifications.models import Notification
from apps.organizations.models import (
    CorporateWebsite,
    Organization,
    OrganizationMember,
)
from apps.reporting.models import GeneratedReport, Report

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    return get_or_create_default_roles()


def _grant(role, module, *actions):
    for a in actions:
        ModuleRight.objects.get_or_create(role=role, module=module, action=a)


def _auth(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return c


@pytest.fixture
def cj_admin(roles):
    r = roles["cj_admin"]
    _grant(r, "organizations", "view", "add", "change", "delete")
    return User.objects.create_user(email="cj@t.com", password="pw", is_active=True, role=r)


@pytest.fixture
def org(db):
    return Organization.objects.create(name="Acme Corp", type="corporate")


def _member(org, roles, email, is_admin=False, group=None):
    u = User.objects.create_user(
        email=email, password="pw", is_active=True, role=roles["individual"]
    )
    OrganizationMember.objects.create(organization=org, user=u, is_admin=is_admin, group=group)
    return u


# --------------------------------------------------------------------------
# Phase 2 — WP-D: schedule assessment + notify (CJ_UC053)
# --------------------------------------------------------------------------


def test_schedule_notifies_org_members(cj_admin, org, roles):
    emp1 = _member(org, roles, "e1@t.com")
    emp2 = _member(org, roles, "e2@t.com")
    assessment = Assessment.objects.create(title="Aptitude", status="published")
    c = _auth(cj_admin)
    resp = c.post(
        f"/api/organizations/{org.id}/schedules/",
        {"assessment": assessment.id, "scheduled_at": timezone.now().isoformat()},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["data"]["notified"] is True
    assert Notification.objects.filter(recipient=emp1).exists()
    assert Notification.objects.filter(recipient=emp2).exists()


def test_schedule_group_only_notifies_group_members(cj_admin, org, roles):
    from apps.organizations.models import Group

    grp = Group.objects.create(organization=org, name="Sales")
    in_group = _member(org, roles, "ing@t.com", group=grp)
    out_group = _member(org, roles, "outg@t.com")
    assessment = Assessment.objects.create(title="A", status="published")
    c = _auth(cj_admin)
    resp = c.post(
        f"/api/organizations/{org.id}/schedules/",
        {"assessment": assessment.id, "group": grp.id, "scheduled_at": timezone.now().isoformat()},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert Notification.objects.filter(recipient=in_group).exists()
    assert not Notification.objects.filter(recipient=out_group).exists()


# --------------------------------------------------------------------------
# Phase 2 — WP-G: corporate report scoping (Doc 4)
# --------------------------------------------------------------------------


def test_corporate_manager_sees_only_own_employees_reports(roles):
    r = roles["corp_admin"]
    _grant(r, "organizations", "view")
    org1 = Organization.objects.create(name="Org1", type="corporate")
    org2 = Organization.objects.create(name="Org2", type="corporate")
    manager = User.objects.create_user(email="mgr@t.com", password="pw", is_active=True, role=r)
    OrganizationMember.objects.create(organization=org1, user=manager, is_admin=True)

    emp1 = _member(org1, roles, "emp1@t.com")
    emp2 = _member(org2, roles, "emp2@t.com")
    rep = Report.objects.create(title="R")
    a = Assessment.objects.create(title="A", status="published")
    s1 = AssessmentSession.objects.create(assessment=a, candidate=emp1, status="completed")
    s2 = AssessmentSession.objects.create(assessment=a, candidate=emp2, status="completed")
    GeneratedReport.objects.create(report=rep, session=s1, candidate=emp1, status="generated")
    GeneratedReport.objects.create(report=rep, session=s2, candidate=emp2, status="generated")

    resp = _auth(manager).get("/api/reporting/generated/")
    assert resp.status_code == 200, resp.data
    rows = (
        resp.data["results"]
        if isinstance(resp.data, dict) and "results" in resp.data
        else resp.data
    )
    candidate_ids = {row["candidate"] for row in rows}
    assert emp1.id in candidate_ids
    assert emp2.id not in candidate_ids


# --------------------------------------------------------------------------
# Phase 3 — WP-E/WP-F: customize page + create website (CJ_UC054/UC055)
# --------------------------------------------------------------------------


def test_create_website_generates_admin_and_slug(cj_admin, org):
    c = _auth(cj_admin)
    resp = c.post(
        f"/api/organizations/{org.id}/website/",
        {"company_name": "Acme Corporation", "layout": "modern", "primary_color": "#ff0000"},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    data = resp.data["data"]
    assert data["slug"] == "acme-corporation"
    assert data["layout"] == "modern"
    # Generated admin credentials returned exactly once.
    creds = data["generated_credentials"]
    assert creds["email"] and creds["temporary_password"]
    website = CorporateWebsite.objects.get(organization=org)
    assert website.admin_user is not None
    assert website.admin_user.role.name == "corp_admin"
    # The generated admin is an admin member of the org.
    assert OrganizationMember.objects.filter(
        organization=org, user=website.admin_user, is_admin=True
    ).exists()


def test_website_is_singleton_per_org(cj_admin, org):
    c = _auth(cj_admin)
    first = c.post(
        f"/api/organizations/{org.id}/website/",
        {"company_name": "Acme"},
        format="json",
    )
    assert first.status_code == 201
    dup = c.post(
        f"/api/organizations/{org.id}/website/",
        {"company_name": "Acme"},
        format="json",
    )
    assert dup.status_code == 400


def test_customize_website(cj_admin, org):
    c = _auth(cj_admin)
    c.post(f"/api/organizations/{org.id}/website/", {"company_name": "Acme"}, format="json")
    resp = c.patch(
        f"/api/organizations/{org.id}/website/",
        {"layout": "minimal", "logo_url": "https://x/logo.png", "primary_color": "#00ff00"},
        format="json",
    )
    assert resp.status_code == 200, resp.data
    assert resp.data["data"]["layout"] == "minimal"
    assert resp.data["data"]["logo_url"] == "https://x/logo.png"


def test_public_site_config_no_auth(cj_admin, org):
    _auth(cj_admin).post(
        f"/api/organizations/{org.id}/website/",
        {"company_name": "Acme Public", "layout": "classic"},
        format="json",
    )
    website = CorporateWebsite.objects.get(organization=org)
    # No credentials — public endpoint.
    resp = APIClient().get(f"/api/organizations/site/{website.slug}/")
    assert resp.status_code == 200, resp.data
    data = resp.data["data"]
    assert data["company_name"] == "Acme Public"
    assert data["primary_color"]
    assert "generated_credentials" not in data


def test_public_site_unknown_slug_404():
    resp = APIClient().get("/api/organizations/site/nope/")
    assert resp.status_code == 404

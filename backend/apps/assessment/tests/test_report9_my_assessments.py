"""Report 9 #72: an individual takes / resumes only the assessments he paid
for (or that are free, or licensed to his organization). The list tells the
page which ones are unlocked so it can split "My Assessments" from "Browse"."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment
from apps.organizations.models import Organization, OrganizationAssignment, OrganizationMember
from apps.payments.models import Payment

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _user(roles, email):
    return User.objects.create_user(
        email=email, password="pw", is_active=True, role=roles["individual"], full_name=email
    )


def _client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


def _unlocked(user):
    resp = _client(user).get("/api/assessments/")
    assert resp.status_code == 200
    return {a["title"]: a["is_unlocked"] for a in resp.data["data"]["results"]}


def test_list_marks_free_and_paid_assessments_unlocked(roles):
    ind = _user(roles, "ind@t.com")
    Assessment.objects.create(title="Free", status="published")
    paid = Assessment.objects.create(title="Paid", status="published", price=500)
    Assessment.objects.create(title="Unpaid", status="published", price=500)
    pending = Assessment.objects.create(title="Pending", status="published", price=500)
    Payment.objects.create(
        user=ind, module="assessment", item_id=paid.id, amount=500, status="paid"
    )
    Payment.objects.create(
        user=ind, module="assessment", item_id=pending.id, amount=500, status="pending"
    )
    assert _unlocked(ind) == {"Free": True, "Paid": True, "Unpaid": False, "Pending": False}
    # Someone else's payment unlocks nothing for him.
    assert _unlocked(_user(roles, "other@t.com"))["Paid"] is False


def test_licensed_priced_assessment_is_unlocked_and_starts_for_member(roles):
    org = Organization.objects.create(name="Corp", type="corporate")
    emp = _user(roles, "emp@t.com")
    OrganizationMember.objects.create(organization=org, user=emp)
    licensed = Assessment.objects.create(title="Licensed", status="published", price=500)
    OrganizationAssignment.objects.create(
        organization=org, item_type="assessment", item_id=licensed.id
    )
    assert _unlocked(emp) == {"Licensed": True}
    # The organization's licence pays: no 402 for the member.
    resp = _client(emp).post(f"/api/assessments/{licensed.id}/start_session/")
    assert resp.status_code == 201, resp.data


def test_unpaid_priced_assessment_still_requires_payment(roles):
    ind = _user(roles, "ind@t.com")
    priced = Assessment.objects.create(title="Priced", status="published", price=500)
    resp = _client(ind).post(f"/api/assessments/{priced.id}/start_session/")
    assert resp.status_code == 402

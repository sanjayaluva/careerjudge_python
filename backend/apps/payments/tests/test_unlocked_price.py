"""Code review: API checkout never charges for an item the user's
organization has unlocked for him — licensed by CJ Admin (members and
managers alike) or his exclusive organization's own private item."""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role, User
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from apps.accounts.services import get_or_create_default_roles
from apps.assessment.models import Assessment
from apps.organizations.models import Organization, OrganizationAssignment, OrganizationMember
from apps.payments.models import Payment
from apps.training.models import TrainingCourse

pytestmark = pytest.mark.django_db


@pytest.fixture
def roles(db):
    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _member(roles, org, role="individual", is_admin=False, email="m@test.com"):
    user = User.objects.create_user(email=email, password="pw", is_active=True, role=roles[role])
    OrganizationMember.objects.create(organization=org, user=user, is_admin=is_admin)
    return user


def _checkout(user, module, item_id):
    c = APIClient()
    c.force_authenticate(user=user)
    resp = c.post("/api/payments/checkout/", {"module": module, "item_id": item_id}, format="json")
    assert resp.status_code == 200, resp.data
    return Payment.objects.get(user=user, module=module, item_id=item_id)


def _license(org, item_type, item_id):
    OrganizationAssignment.objects.create(organization=org, item_type=item_type, item_id=item_id)


def test_licensed_assessment_is_free_for_a_member(roles):
    org = Organization.objects.create(name="Acme", type="corporate")
    member = _member(roles, org)
    a = Assessment.objects.create(title="Paid", status="published", price=Decimal("500.00"))
    _license(org, "assessment", a.id)
    payment = _checkout(member, "assessment", a.id)
    assert payment.amount == 0 and payment.status == "free"


def test_licensed_course_is_free_for_a_manager(roles):
    org = Organization.objects.create(name="Acme", type="corporate")
    manager = _member(roles, org, role="corp_admin", is_admin=True)
    course = TrainingCourse.objects.create(title="Paid", status="published", price=300)
    _license(org, "training_course", course.id)
    payment = _checkout(manager, "training", course.id)
    assert payment.amount == 0 and payment.status == "free"


def test_private_course_is_free_for_its_organizations_member(roles):
    org = Organization.objects.create(name="Excl", type="corp_exclusive")
    member = _member(roles, org)
    course = TrainingCourse.objects.create(
        title="Own", status="published", price=300, owner_organization=org
    )
    payment = _checkout(member, "training", course.id)
    assert payment.amount == 0 and payment.status == "free"


def test_unlicensed_course_keeps_its_price(roles):
    org = Organization.objects.create(name="Acme", type="corporate")
    member = _member(roles, org)
    course = TrainingCourse.objects.create(title="Paid", status="published", price=300)
    payment = _checkout(member, "training", course.id)
    assert payment.amount == Decimal("300.00") and payment.status == "pending"

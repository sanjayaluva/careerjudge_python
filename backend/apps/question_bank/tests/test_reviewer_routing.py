"""E-X3: SME→Reviewer same-domain routing."""

import pytest

from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.question_bank.models import Category, Question
from apps.question_bank.views import _pick_domain_reviewer

pytestmark = pytest.mark.django_db


def _roles():
    from apps.accounts.models import ModuleRight, Role
    from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights

    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return roles


def _q(**kw):
    defaults = {
        "question_type": "MCQ_TEXT_IMAGE",
        "question_title": "T",
        "question_text_1": "Q?",
        "scoring_type": "BINARY",
    }
    defaults.update(kw)
    return Question.objects.create(**defaults)


def test_routes_to_in_domain_reviewer():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme-x3@test.com")
    reviewer_quant = UserFactory(role=roles["reviewer"], email="rq@test.com")
    reviewer_other = UserFactory(role=roles["reviewer"], email="ro@test.com")

    quant = Category.objects.create(name="Quant")
    algebra = Category.objects.create(name="Algebra", parent=quant)
    verbal = Category.objects.create(name="Verbal")

    # reviewer_quant has authored a question in the Quant domain (Algebra child);
    # reviewer_other only works in Verbal.
    _q(category=algebra, created_by=reviewer_quant)
    _q(category=verbal, created_by=reviewer_other)

    sme_question = _q(category=algebra, created_by=sme)
    chosen = _pick_domain_reviewer(sme_question)
    assert chosen == reviewer_quant


def test_falls_back_to_any_reviewer_when_no_domain_match():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme2@test.com")
    reviewer = UserFactory(role=roles["reviewer"], email="rev2@test.com")
    cat = Category.objects.create(name="NewDomain")
    q = _q(category=cat, created_by=sme)
    # No reviewer has worked in this domain → any active reviewer.
    assert _pick_domain_reviewer(q) == reviewer


def test_never_self_assigns_author():
    roles = _roles()
    reviewer = UserFactory(role=roles["reviewer"], email="rev3@test.com")
    cat = Category.objects.create(name="Solo")
    # The only reviewer is also the author.
    q = _q(category=cat, created_by=reviewer)
    assert _pick_domain_reviewer(q) is None


def test_no_reviewers_returns_none():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme4@test.com")
    cat = Category.objects.create(name="Empty")
    q = _q(category=cat, created_by=sme)
    assert _pick_domain_reviewer(q) is None


def test_least_loaded_reviewer_chosen():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme5@test.com")
    busy = UserFactory(role=roles["reviewer"], email="busy@test.com")
    free = UserFactory(role=roles["reviewer"], email="free@test.com")
    dom = Category.objects.create(name="Dom")
    # Both are in-domain (authored here).
    _q(category=dom, created_by=busy)
    _q(category=dom, created_by=free)
    # busy already has an assigned pending question.
    _q(category=dom, created_by=sme, status="pending_content_review", assigned_reviewer=busy)
    q = _q(category=dom, created_by=sme)
    assert _pick_domain_reviewer(q) == free


# ---------------------------------------------------------------------------
# Report 9 #71: a sent-back question returns to the SAME reviewer.
# ---------------------------------------------------------------------------


def _client(user):
    from rest_framework.test import APIClient

    c = APIClient()
    c.force_authenticate(user)
    return c


def _submit(sme, q):
    resp = _client(sme).post(f"/api/question-bank/questions/{q.id}/submit_for_review/")
    assert resp.status_code == 200, resp.content
    q.refresh_from_db()
    return q


def _send_back(reviewer, q):
    resp = _client(reviewer).post(
        f"/api/question-bank/questions/{q.id}/review/",
        {
            "review_type": "content",
            "action": "send_back",
            "comment": "Fix the wording",
        },
        format="json",
    )
    assert resp.status_code == 200, resp.content
    q.refresh_from_db()
    assert q.status == "sent_back"
    return q


def _statement(sme, cat):
    return _q(
        category=cat,
        created_by=sme,
        question_type="PSYCHOMETRIC_STATEMENT",
        scoring_type="",
    )


def test_resubmitted_question_returns_to_reviewer_who_sent_it_back():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme71@test.com")
    first = UserFactory(role=roles["reviewer"], email="first71@test.com")
    other = UserFactory(role=roles["reviewer"], email="other71@test.com")
    cat = Category.objects.create(name="D71")
    q = _submit(sme, _statement(sme, cat))
    sent_to = q.assigned_reviewer
    assert sent_to in (first, other)
    _send_back(sent_to, q)
    # Make the original reviewer the busiest so a fresh pick would choose
    # the other reviewer.
    for _ in range(3):
        _q(category=cat, created_by=sme, status="pending_content_review", assigned_reviewer=sent_to)
    from apps.notifications.models import Notification

    Notification.objects.all().delete()
    q = _submit(sme, q)
    assert q.status == "pending_content_review"
    assert q.assigned_reviewer == sent_to
    # Only the routed reviewer is told; the other reviewer gets nothing.
    other_reviewer = other if sent_to == first else first
    assert Notification.objects.filter(recipient=sent_to).exists()
    assert not Notification.objects.filter(recipient=other_reviewer).exists()


def test_resubmission_reroutes_when_original_reviewer_inactive():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme71b@test.com")
    gone = UserFactory(role=roles["reviewer"], email="gone71@test.com")
    cat = Category.objects.create(name="D71b")
    q = _submit(sme, _statement(sme, cat))
    assert q.assigned_reviewer == gone
    _send_back(gone, q)
    gone.is_active = False
    gone.save(update_fields=["is_active"])
    backup = UserFactory(role=roles["reviewer"], email="backup71@test.com")
    q = _submit(sme, q)
    assert q.assigned_reviewer == backup


def test_send_back_keeps_question_with_same_sme():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme71c@test.com")
    UserFactory(role=roles["reviewer"], email="rev71c@test.com")
    cat = Category.objects.create(name="D71c")
    q = _submit(sme, _statement(sme, cat))
    q = _send_back(q.assigned_reviewer, q)
    assert q.created_by == sme

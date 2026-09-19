"""E-X3: SME→Reviewer same-domain routing."""

import pytest

from apps.accounts.services import get_or_create_default_roles
from apps.accounts.tests.factories import UserFactory
from apps.question_bank.models import Category, Question
from apps.question_bank.views import _pick_domain_reviewer

pytestmark = pytest.mark.django_db


def _roles():
    return get_or_create_default_roles()


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

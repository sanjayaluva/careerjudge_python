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


# ---------------------------------------------------------------------------
# Report 9 #65: the SME picks the reviewer (pre-selected from his task).
# ---------------------------------------------------------------------------


def _sme_task(admin, sme, reviewer, category_name="", status="in_progress"):
    from apps.tasks.models import Task, TaskSpec

    task = Task.objects.create(
        title="Write questions",
        description="d",
        assigned_by=admin,
        assigned_to=sme,
        assignee_role="sme",
        status=status,
        reviewer=reviewer,
    )
    if category_name:
        TaskSpec.objects.create(task=task, qb_category=category_name)
    return task


def test_submit_goes_to_the_reviewer_the_sme_chose():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme65a@test.com")
    UserFactory(role=roles["reviewer"], email="idle65a@test.com")
    chosen = UserFactory(role=roles["reviewer"], email="chosen65a@test.com")
    cat = Category.objects.create(name="D65a")
    # Make the chosen reviewer the busiest, so least-busy routing would not
    # have picked him.
    for _ in range(2):
        _q(category=cat, created_by=sme, status="pending_content_review", assigned_reviewer=chosen)
    q = _statement(sme, cat)
    resp = _client(sme).post(
        f"/api/question-bank/questions/{q.id}/submit_for_review/",
        {"reviewer": chosen.id},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    q.refresh_from_db()
    assert q.assigned_reviewer == chosen
    from apps.notifications.models import Notification

    assert Notification.objects.filter(recipient=chosen).exists()


def test_submit_rejects_a_non_reviewer_or_inactive_choice():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme65b@test.com")
    psy = UserFactory(role=roles["psychometrician"], email="psy65b@test.com")
    gone = UserFactory(role=roles["reviewer"], email="gone65b@test.com", is_active=False)
    cat = Category.objects.create(name="D65b")
    q = _statement(sme, cat)
    for bad in (psy.id, gone.id, sme.id, 999999, "x"):
        resp = _client(sme).post(
            f"/api/question-bank/questions/{q.id}/submit_for_review/",
            {"reviewer": bad},
            format="json",
        )
        assert resp.status_code == 400, bad
    q.refresh_from_db()
    assert q.status == "draft"


def test_submit_without_choice_uses_the_reviewer_named_on_the_task():
    roles = _roles()
    admin = UserFactory(role=roles["cj_admin"], email="adm65c@test.com")
    sme = UserFactory(role=roles["sme"], email="sme65c@test.com")
    UserFactory(role=roles["reviewer"], email="idle65c@test.com")
    named = UserFactory(role=roles["reviewer"], email="named65c@test.com")
    cat = Category.objects.create(name="D65c")
    for _ in range(2):
        _q(category=cat, created_by=sme, status="pending_content_review", assigned_reviewer=named)
    _sme_task(admin, sme, named)
    q = _submit(sme, _statement(sme, cat))
    assert q.assigned_reviewer == named


def test_submit_without_choice_or_task_falls_back_to_auto_routing():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme65d@test.com")
    only = UserFactory(role=roles["reviewer"], email="only65d@test.com")
    cat = Category.objects.create(name="D65d")
    q = _submit(sme, _statement(sme, cat))
    assert q.assigned_reviewer == only


def test_reviewer_options_lists_pool_with_domains_and_task_default():
    from apps.accounts.models import UserProfile

    roles = _roles()
    admin = UserFactory(role=roles["cj_admin"], email="adm65e@test.com")
    sme = UserFactory(role=roles["sme"], email="sme65e@test.com")
    r1 = UserFactory(role=roles["reviewer"], email="r1-65e@test.com", full_name="Asha")
    r2 = UserFactory(role=roles["reviewer"], email="r2-65e@test.com", full_name="Biju")
    UserFactory(role=roles["reviewer"], email="off65e@test.com", is_active=False)
    UserFactory(role=roles["psychometrician"], email="psy65e@test.com")
    UserProfile.objects.update_or_create(
        user=r2, defaults={"domains_of_expertise": ["Verbal", "Logic"]}
    )
    verbal = Category.objects.create(name="Verbal")
    quant = Category.objects.create(name="Quant")
    _sme_task(admin, sme, r1, category_name="Quant")
    _sme_task(admin, sme, r2, category_name="Verbal")
    # A cancelled task naming r1 for Verbal does not count.
    _sme_task(admin, sme, r1, category_name="Verbal", status="cancelled")
    q = _statement(sme, verbal)
    resp = _client(sme).get(f"/api/question-bank/questions/{q.id}/reviewer-options/")
    assert resp.status_code == 200, resp.content
    data = resp.json()["data"]
    assert [r["id"] for r in data["reviewers"]] == [r1.id, r2.id]
    assert data["reviewers"][1]["domains_of_expertise"] == ["Verbal", "Logic"]
    assert data["default_reviewer"] == r2.id
    assert data["task_reviewer"] == r2.id
    assert data["locked"] is False
    q2 = _statement(sme, quant)
    data = _client(sme).get(f"/api/question-bank/questions/{q2.id}/reviewer-options/").json()
    assert data["data"]["default_reviewer"] == r1.id


def test_reviewer_options_locked_to_the_reviewer_who_sent_it_back():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme65f@test.com")
    first = UserFactory(role=roles["reviewer"], email="first65f@test.com")
    other = UserFactory(role=roles["reviewer"], email="other65f@test.com")
    cat = Category.objects.create(name="D65f")
    q = _statement(sme, cat)
    resp = _client(sme).post(
        f"/api/question-bank/questions/{q.id}/submit_for_review/",
        {"reviewer": first.id},
        format="json",
    )
    assert resp.status_code == 200
    q.refresh_from_db()
    _send_back(first, q)
    data = _client(sme).get(f"/api/question-bank/questions/{q.id}/reviewer-options/").json()
    assert data["data"]["default_reviewer"] == first.id
    assert data["data"]["locked"] is True
    # Report 9 #71 still holds: the resubmission returns to the same reviewer
    # even if another one is picked.
    resp = _client(sme).post(
        f"/api/question-bank/questions/{q.id}/submit_for_review/",
        {"reviewer": other.id},
        format="json",
    )
    assert resp.status_code == 200
    q.refresh_from_db()
    assert q.assigned_reviewer == first


def test_sme_cannot_list_reviewers_for_another_smes_question():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme65g@test.com")
    other_sme = UserFactory(role=roles["sme"], email="osme65g@test.com")
    cat = Category.objects.create(name="D65g")
    q = _statement(other_sme, cat)
    resp = _client(sme).get(f"/api/question-bank/questions/{q.id}/reviewer-options/")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Report 9 #92: a resubmission returns to the psychometrician who sent it back.
# ---------------------------------------------------------------------------


def _review(user, q, review_type, action, **extra):
    payload = {"review_type": review_type, "action": action, **extra}
    if action == "approve":
        payload.setdefault("rating", 4)
    if action == "send_back":
        payload.setdefault("comment", "Please revise")
    resp = _client(user).post(
        f"/api/question-bank/questions/{q.id}/review/", payload, format="json"
    )
    assert resp.status_code == 200, resp.content
    q.refresh_from_db()
    return q


def test_resubmission_returns_to_psychometrician_who_sent_it_back():
    from apps.notifications.models import Notification

    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme92@test.com")
    reviewer = UserFactory(role=roles["reviewer"], email="rev92@test.com")
    psy = UserFactory(role=roles["psychometrician"], email="psy92@test.com")
    other_psy = UserFactory(role=roles["psychometrician"], email="opsy92@test.com")
    cat = Category.objects.create(name="D92")
    q = _submit(sme, _statement(sme, cat))
    q = _review(reviewer, q, "content", "approve")
    assert q.status == "pending_psychometric_review"
    assert q.assigned_psychometrician is None
    q = _review(psy, q, "psychometric", "send_back")
    assert q.status == "sent_back"
    assert q.assigned_psychometrician == psy

    Notification.objects.all().delete()
    q = _submit(sme, q)
    # Existing flow: content review first, by the same reviewer (#71).
    assert q.status == "pending_content_review"
    assert q.assigned_reviewer == reviewer
    q = _review(reviewer, q, "content", "approve")
    assert q.status == "pending_psychometric_review"
    assert q.assigned_psychometrician == psy
    assert Notification.objects.filter(
        recipient=psy, title__icontains="psychometric review"
    ).exists()
    assert not Notification.objects.filter(recipient=other_psy).exists()

    # It is in his "Assigned to me" queue, not the other psychometrician's.
    mine = _client(psy).get("/api/question-bank/questions/?assigned=me").json()["data"]
    assert [r["id"] for r in mine["results"]] == [q.id]
    theirs = _client(other_psy).get("/api/question-bank/questions/?assigned=me").json()["data"]
    assert theirs["results"] == []


def test_psychometrician_no_longer_active_is_not_routed():
    roles = _roles()
    sme = UserFactory(role=roles["sme"], email="sme92b@test.com")
    reviewer = UserFactory(role=roles["reviewer"], email="rev92b@test.com")
    psy = UserFactory(role=roles["psychometrician"], email="psy92b@test.com")
    cat = Category.objects.create(name="D92b")
    q = _submit(sme, _statement(sme, cat))
    q = _review(reviewer, q, "content", "approve")
    q = _review(psy, q, "psychometric", "send_back")
    psy.is_active = False
    psy.save(update_fields=["is_active"])
    q = _submit(sme, q)
    q = _review(reviewer, q, "content", "approve")
    assert q.status == "pending_psychometric_review"
    assert q.assigned_psychometrician is None

"""Session delivery set + order (Doc 3 §5.1) — Report 7 #1-#10, #12, #14, #15,
#18-#20, #33, #34, #42.

Structure mirrors the client's test assessment: 3 sections x 2 subsections,
questions assigned only at the leaves, one multi-sub-question item.
"""

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import ModuleRight, Role, User
from apps.assessment.models import (
    Assessment,
    AssessmentQuestion,
    AssessmentSection,
    AssessmentSession,
    QuestionAttempt,
)
from apps.assessment.views import _seed_session_attempts
from apps.question_bank.models import Question

pytestmark = pytest.mark.django_db


def _q(title, qtype="MCQ_TEXT_IMAGE", subs=1):
    return Question.objects.create(
        question_type=qtype,
        question_title=title,
        question_text_1=title,
        status="confirmed",
        sub_question_count=subs,
    )


def _user(role_name, email):
    role, _ = Role.objects.get_or_create(name=role_name, defaults={"is_system": True})
    return User.objects.create_user(email=email, password="pw", is_active=True, role=role)


@pytest.fixture
def admin_client():
    user = _user("cj_admin", "admin@t.com")
    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=user.role, module="assessment", action=action)
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def built(admin_client):
    """Build the structure through the API, as the authoring UI does (no
    explicit `order`), so creation order must become the configured order."""
    a = Assessment.objects.create(title="Std", assessment_type="normal", status="published")
    base = f"/api/assessments/{a.id}/sections/"
    leaves = {}
    for s in (1, 2, 3):
        sec = admin_client.post(base, {"title": f"Section {s}"}, format="json").data["data"]
        for sub in (1, 2):
            leaf = admin_client.post(
                base, {"title": f"Subsection {sub}", "parent": sec["id"]}, format="json"
            ).data["data"]
            leaves[(s, sub)] = leaf["id"]
    # Two questions per leaf, assigned in order A then B; (1,1)'s B has 3 subs.
    qs = {}
    for (s, sub), leaf_id in leaves.items():
        for label in ("A", "B"):
            subs = 3 if (s, sub, label) == (1, 1, "B") else 1
            qtype = "MCQ_AUDIO_MULTI" if subs > 1 else "MCQ_TEXT_IMAGE"
            q = _q(f"S{s}.{sub}{label}", qtype, subs)
            r = admin_client.post(f"{base}{leaf_id}/questions/", {"question": q.id}, format="json")
            assert r.status_code == 201, r.data
            qs[(s, sub, label)] = q
    return a, leaves, qs


def _session(a):
    cand = _user("individual", "cand@t.com")
    session = AssessmentSession.objects.create(assessment=a, candidate=cand, status="active")
    _seed_session_attempts(session)
    client = APIClient()
    client.force_authenticate(cand)
    return session, client


def _titles(client, session):
    resp = client.get(f"/api/assessments/sessions/{session.id}/questions/")
    assert resp.status_code == 200, resp.data
    return [u["question_detail"]["question_title"] for u in resp.data["data"]], resp.data["data"]


STATIC = [f"S{s}.{sub}{x}" for s in (1, 2, 3) for sub in (1, 2) for x in ("A", "B")]


def test_static_delivery_follows_configured_tree(built):
    a, _leaves, _qs = built
    session, client = _session(a)
    titles, units = _titles(client, session)
    # Parent before child, subsections in order, questions in assigned order —
    # not level-first (which interleaved Section 1/2/3 subsections) and not
    # reversed (all order=0).
    assert titles == STATIC
    assert units[0]["section_path"] == ["Section 1", "Subsection 1"]


def test_sub_question_answers_do_not_become_extra_questions(built):
    a, leaves, qs = built
    session, client = _session(a)
    multi = qs[(1, 1, "B")]
    for idx in (0, 1, 2):
        r = client.post(
            f"/api/assessments/sessions/{session.id}/answer/",
            {"question_id": multi.id, "sub_question_index": idx, "raw_answer": {"i": idx}},
            format="json",
        )
        assert r.status_code == 200
    # Sub-question rows inherit the question's section (not sections.first()).
    assert set(
        QuestionAttempt.objects.filter(session=session, question=multi).values_list(
            "section_id", flat=True
        )
    ) == {leaves[(1, 1)]}

    # Resume: still one entry per assigned question (12), same order, and the
    # entry carries every sub-answer so the player can restore state.
    titles, units = _titles(client, session)
    assert titles == STATIC
    unit = next(u for u in units if u["question"] == multi.id)
    assert unit["sub_answers"] == {
        str(i): {"status": "attempted", "raw_answer": {"i": i}} for i in (0, 1, 2)
    }


def test_random_subsection_shuffles_below_it_only(built):
    a, leaves, _qs = built
    # Section 2 is RANDOM: its subsections and their questions may shuffle;
    # Sections 1 and 3 (and the Section 1 -> 2 -> 3 order) stay static.
    sec2 = AssessmentSection.objects.get(assessment=a, title="Section 2", parent=None)
    sec2.order_mode = "RANDOM"
    sec2.save()
    session, client = _session(a)
    titles, _ = _titles(client, session)
    assert titles[:4] == STATIC[:4]
    assert titles[8:] == STATIC[8:]
    assert sorted(titles[4:8]) == sorted(STATIC[4:8])

    # Stable per session: refresh/resume/Previous see the same order.
    again, _ = _titles(client, session)
    assert again == titles

    # And it really does shuffle across sessions.
    orders = set()
    for _ in range(12):
        s2 = AssessmentSession.objects.create(
            assessment=a, candidate=session.candidate, status="active"
        )
        _seed_session_attempts(s2)
        t, _ = _titles(client, s2)
        assert t[:4] == STATIC[:4] and t[8:] == STATIC[8:]
        orders.add(tuple(t[4:8]))
    assert len(orders) > 1


def test_created_sections_and_questions_get_sequential_order(built):
    a, leaves, _qs = built
    roots = AssessmentSection.objects.filter(assessment=a, parent=None)
    assert [s.order for s in roots.order_by("order")] == [1, 2, 3]
    assert list(
        AssessmentQuestion.objects.filter(section_id=leaves[(2, 1)]).values_list("order", flat=True)
    ) == [1, 2]


def test_detail_lists_top_level_sections_once_with_nested_children(built, admin_client):
    a, _leaves, _qs = built
    data = admin_client.get(f"/api/assessments/{a.id}/").data["data"]
    assert [s["title"] for s in data["sections"]] == ["Section 1", "Section 2", "Section 3"]
    assert [c["title"] for c in data["sections"][0]["subsections"]] == [
        "Subsection 1",
        "Subsection 2",
    ]


def test_timer_can_be_set_at_only_one_level(built, admin_client):
    """Doc 3 §5.2 / Report 7 #11: durations only at the configured level."""
    a, leaves, _qs = built
    base = f"/api/assessments/{a.id}/sections/"
    sec1 = AssessmentSection.objects.get(assessment=a, title="Section 1", parent=None)

    # Timer level = Level 2: a Level 1 duration is rejected, Level 2 accepted.
    a.timer_level = "level2"
    a.save()
    r = admin_client.patch(f"{base}{sec1.id}/", {"duration_seconds": 420}, format="json")
    assert r.status_code == 400
    assert "only one level" in str(r.data).lower() or "one level" in str(r.content).lower()
    r = admin_client.patch(f"{base}{leaves[(1, 1)]}/", {"duration_seconds": 240}, format="json")
    assert r.status_code == 200
    # Clearing a duration is always allowed.
    r = admin_client.patch(f"{base}{sec1.id}/", {"duration_seconds": None}, format="json")
    assert r.status_code == 200

    # Per-question timers only when the timer level is 'question'.
    aq = AssessmentQuestion.objects.filter(section_id=leaves[(1, 1)]).first()
    url = f"{base}{leaves[(1, 1)]}/questions/{aq.id}/"
    assert admin_client.patch(url, {"duration_seconds": 30}, format="json").status_code == 400
    a.timer_level = "question"
    a.save()
    assert admin_client.patch(url, {"duration_seconds": 30}, format="json").status_code == 200

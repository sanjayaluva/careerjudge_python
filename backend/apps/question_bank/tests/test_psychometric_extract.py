"""Report 9 #87/#88: Psychometric Analysis extract → select → run.

Doc 1 §4.1.1: "User specifies filter criteria and clicks 'Extract' … System
extracts questions … and lists them … User … selects by checking each one or
by 'select all'". A main category must cover its subcategories' questions.
"""

import pytest

from apps.assessment.models import Assessment
from apps.question_bank.models import Category, Question

from .test_dossier_gaps import (
    _client_for,
    _make_attempt,
    _make_candidate,
    _make_completed_session,
    _make_question,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def psy_client(db):
    from apps.accounts.models import ModuleRight, Role
    from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
    from apps.accounts.services import get_or_create_default_roles
    from apps.accounts.tests.factories import UserFactory

    roles = get_or_create_default_roles()
    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)
    return _client_for(UserFactory(role=roles["psychometrician"], email="psy-extract@test.com"))


EXTRACT = "/api/question-bank/questions/psychometric-extract/"
RUN = "/api/question-bank/questions/psychometric_analysis/"


def _tree():
    main = Category.objects.create(name="Section 2")
    sub = Category.objects.create(name="Part A", parent=main)
    subsub = Category.objects.create(name="Part A1", parent=sub)
    other = Category.objects.create(name="Elsewhere")
    q_main = _make_question(category=main, question_title="Direct")
    q_sub = _make_question(category=sub, question_title="Sub")
    q_subsub = _make_question(category=subsub, question_title="SubSub")
    q_other = _make_question(category=other, question_title="Other")
    return main, sub, (q_main, q_sub, q_subsub, q_other)


def test_extract_main_category_includes_subcategories(psy_client):
    main, _sub, (q_main, q_sub, q_subsub, _q_other) = _tree()
    resp = psy_client.post(EXTRACT, {"category_id": main.id}, format="json")
    assert resp.status_code == 200, resp.content
    rows = resp.json()["data"]
    assert [r["id"] for r in rows] == [q_main.id, q_sub.id, q_subsub.id]
    row = rows[1]
    assert row["question_title"] == "Sub"
    assert row["category_path"] == "Section 2 > Part A"
    assert row["n_candidates"] == 0
    assert {"question_type_label", "status_label", "item_difficulty_index"} <= row.keys()


def test_extract_stores_nothing(psy_client):
    main, _sub, (q_main, *_rest) = _tree()
    psy_client.post(EXTRACT, {"category_id": main.id}, format="json")
    q_main.refresh_from_db()
    assert q_main.psychometric_analyzed_at is None


def test_extract_counts_candidates_within_data_filters(psy_client):
    q = _make_question()
    assessment = Assessment.objects.create(title="A", status="published")
    for i, state in enumerate(("Karnataka", "Kerala", "Karnataka")):
        c = _make_candidate(f"x{i}@test.com", state_province=state)
        _make_attempt(_make_completed_session(assessment, c, total_score=5), q, score=1.0)
    resp = psy_client.post(
        EXTRACT, {"question_ref": str(q.id), "region": "Karnataka"}, format="json"
    )
    assert resp.status_code == 200, resp.content
    assert [(r["id"], r["n_candidates"]) for r in resp.json()["data"]] == [(q.id, 2)]


def test_question_id_filter_matches_ids_and_labels(psy_client):
    a = _make_question(question_id_label="QB-0007")
    b = _make_question()
    _make_question()
    resp = psy_client.post(EXTRACT, {"question_ref": f"qb-0007, #{b.id}"}, format="json")
    assert resp.status_code == 200, resp.content
    assert [r["id"] for r in resp.json()["data"]] == [a.id, b.id]


def test_question_id_filter_combines_with_category(psy_client):
    main, _sub, (q_main, q_sub, _q_subsub, q_other) = _tree()
    resp = psy_client.post(
        EXTRACT,
        {"category_id": main.id, "question_ref": f"{q_sub.id} {q_other.id}"},
        format="json",
    )
    assert [r["id"] for r in resp.json()["data"]] == [q_sub.id]


def test_extract_requires_some_filter(psy_client):
    resp = psy_client.post(EXTRACT, {"region": "Karnataka"}, format="json")
    assert resp.status_code == 400


def test_run_analysis_on_selected_questions_only(psy_client):
    main, _sub, (q_main, q_sub, q_subsub, _q_other) = _tree()
    resp = psy_client.post(
        RUN, {"question_ids": [q_sub.id, q_subsub.id], "category_id": main.id}, format="json"
    )
    assert resp.status_code == 200, resp.content
    assert [r["question_id"] for r in resp.json()["data"]] == [q_sub.id, q_subsub.id]
    q_main.refresh_from_db()
    assert q_main.psychometric_analyzed_at is None
    assert Question.objects.get(id=q_sub.id).psychometric_analyzed_at is not None


def test_run_analysis_by_main_category_includes_subcategories(psy_client):
    main, _sub, (q_main, q_sub, q_subsub, _q_other) = _tree()
    resp = psy_client.post(RUN, {"category_id": main.id}, format="json")
    assert resp.status_code == 200, resp.content
    assert {r["question_id"] for r in resp.json()["data"]} == {q_main.id, q_sub.id, q_subsub.id}

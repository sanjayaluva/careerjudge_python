"""Session delivery order (Doc 3 §5.1) — which attempts the player shows, and
in what order.

Rules implemented here:

* **One entry per assigned question.** Multi-sub-question types (1c-1h,
  2c/2d) are assigned once; their sub-question answers live in extra
  ``QuestionAttempt`` rows (``sub_question_index`` 1..n-1). Those rows are
  answer storage, not deliverable questions — returning them made 17
  assigned questions show as 21+ and grow on every resume (Report 7 #5/#10).
  The anchor row carries every sub-answer so the player can restore state.

* **Static order = the configured tree order.** Parent before child, siblings
  by their assigned ``order`` (ties by creation), questions by their assigned
  order within the section. Sorting by level first interleaved sibling
  subsections of different parents (Report 7 #1/#2/#4).

* **Random is per section and applies below it** (Doc 3 §5.1 display-order
  rules: ordered levels keep their order, everything below the deepest
  ordered level is random). A section whose ``order_mode`` is RANDOM shuffles
  its child sections and questions at every level beneath it; its ancestors
  keep their order (Report 7 #7/#8). Assessment-level RANDOM shuffles the
  whole delivered set, as before.

* **Stable per session.** Shuffles are seeded by the session id, so refreshes,
  resumes and Previous always see the same order (Report 7 #20).
"""

from __future__ import annotations

import random
from collections import defaultdict


def _tree_key(section):
    return (section.order, section.id)


def anchor_attempts(attempts, assigned_keys):
    """Pick the one deliverable attempt per assigned question.

    ``assigned_keys`` is the set of ``(section_id, question_id,
    sub_question_index)`` tuples of the assessment's AssessmentQuestion rows.
    A question with no matching row (legacy data) falls back to its lowest
    sub-question attempt.
    """
    anchors = [
        a for a in attempts if (a.section_id, a.question_id, a.sub_question_index) in assigned_keys
    ]
    covered = {a.question_id for a in anchors}
    fallback = {}
    for a in sorted(attempts, key=lambda x: (x.sub_question_index, x.id)):
        if a.question_id not in covered:
            fallback.setdefault(a.question_id, a)
    return anchors + list(fallback.values())


def sub_answers_by_question(attempts):
    """``{question_id: {sub_index: {"status": .., "raw_answer": ..}}}``."""
    out = defaultdict(dict)
    for a in attempts:
        out[a.question_id][a.sub_question_index] = {
            "status": a.status,
            "raw_answer": a.raw_answer,
        }
    return out


def section_paths(sections_by_id):
    """``{section_id: ["Section 1", "Subsection 2"]}`` — titles root → leaf."""
    paths = {}
    for sid, sec in sections_by_id.items():
        chain, node = [], sec
        while node is not None:
            chain.append(node.title)
            node = sections_by_id.get(node.parent_id)
        paths[sid] = list(reversed(chain))
    return paths


def order_for_delivery(session, anchors, sections_by_id, aq_order, static=False):
    """Return ``anchors`` in delivery order for ``session``.

    ``static=True`` ignores every RANDOM setting and returns the configured
    (assigned) order — used for the sidebar, which lists sections and
    questions in assigned order even when delivery is random (Report 7 #43).
    """
    rng = random.Random(session.id)

    children = defaultdict(list)
    for sec in sections_by_id.values():
        children[sec.parent_id].append(sec)
    for sibs in children.values():
        sibs.sort(key=_tree_key)

    by_section = defaultdict(list)
    orphans = []
    for a in anchors:
        if a.section_id in sections_by_id:
            by_section[a.section_id].append(a)
        else:
            orphans.append(a)
    for items in by_section.values():
        items.sort(
            key=lambda a: (
                aq_order.get((a.section_id, a.question_id, a.sub_question_index), 0),
                a.id,
            )
        )

    ordered = []

    def walk(section, randomise):
        randomise = not static and (randomise or section.order_mode == "RANDOM")
        questions = list(by_section.get(section.id, []))
        kids = list(children.get(section.id, []))
        if randomise:
            rng.shuffle(questions)
            rng.shuffle(kids)
        ordered.extend(questions)
        for kid in kids:
            walk(kid, randomise)

    for root in children.get(None, []):
        walk(root, False)
    ordered.extend(sorted(orphans, key=lambda a: a.id))

    if not static and getattr(session.assessment, "display_order", "STATIC") == "RANDOM":
        rng.shuffle(ordered)
    return ordered

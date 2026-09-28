"""Delivery ordering engine (Report 7 §1-8, §33-34, §42-43).

Implements the SRS 03_assessment_configuration.json "Order of delivery"
rules (§5.1) plus the Report 7 clarifications:

  STATIC delivery ("as configured"):
    Questions are delivered in EXACTLY the assigned order — a depth-first
    walk of the section/variable tree (L1 -> L2 -> ... -> leaf), each node
    visited in its configured ``order`` (siblings ascending), and each
    leaf's questions in their assigned ``order``. (Report 7 §2.)

  RANDOM delivery:
    - Assessment-level RANDOM (``Assessment.display_order == "RANDOM"``):
      the whole question set is shuffled (SRS default-random rule).
      (Report 7 §7: assessment-level randomization "comes out alright".)
    - Per-section ``order_mode == "RANDOM"`` (Report 7 §8): at the section
      where RANDOM is configured, its child subsections are visited in
      shuffled order AND the questions directly under it are shuffled.
      Parent-level sections above it keep their static order —
      randomization cascades downward only, never upward.

  Seeding: shuffles are seeded by the session id, so the delivered order
  is stable across refresh/resume within one session but differs per
  session.

The static (configured) order is ALSO computed and returned as
``static_order_index`` on every attempt row so the player's TEST PROGRESS
sidebar can display the configured structure regardless of delivery
order (Report 7 §43).
"""

import random

from .models import AssessmentQuestion, AssessmentSection


def _ordered_children(parent_id, sections_by_id):
    """Children of a parent, in configured (order, id) ascending order."""
    kids = [s for s in sections_by_id.values() if s.parent_id == parent_id]
    kids.sort(key=lambda s: (s.order, s.id))
    return kids


def _walk_static(sections):
    """Depth-first walk of the section tree in configured order.

    Yields each section exactly once: L1s in ``order`` ascending, each
    followed by its descendants (recursively, in their configured order).
    This is the "as assigned" hierarchy order for STATIC display.
    """
    sections_by_id = {s.id: s for s in sections}
    roots = [s for s in sections if s.parent_id is None]
    roots.sort(key=lambda s: (s.order, s.id))

    stack = list(reversed(roots))  # pop() yields the first root first
    while stack:
        node = stack.pop()
        yield node
        children = _ordered_children(node.id, sections_by_id)
        for child in reversed(children):
            stack.append(child)


def _assigned_question_order(assessment):
    """Map (section_id, question_id, subq) -> assigned order for questions."""
    aq_order = {}
    for aq in AssessmentQuestion.objects.filter(section__assessment=assessment).order_by(
        "section_id", "order", "id"
    ):
        aq_order[(aq.section_id, aq.question_id, aq.sub_question_index)] = aq.order
    return aq_order


def _group_attempts(attempts, aq_order):
    """Group attempts per section; within a section sort by assigned order."""
    per_section = {}
    for att in attempts:
        per_section.setdefault(att.section_id, []).append(att)
    for _sid, atts in per_section.items():
        atts.sort(
            key=lambda a: (
                aq_order.get((a.section_id, a.question_id, a.sub_question_index), 0),
                a.id,
            )
        )
    return per_section


def compute_delivery_order(assessment, attempts, session_id):
    """Order the given QuestionAttempt rows for delivery.

    Returns a list of ``(static_index, attempt)`` tuples in DELIVERY order.
    ``static_index`` is the row's position in the fully-static (configured)
    order — used by the player sidebar (Report 7 §43). ``attempts`` must be
    a list with ``section`` populated.
    """
    sections = list(AssessmentSection.objects.filter(assessment=assessment))
    sections_by_id = {s.id: s for s in sections}
    aq_order = _assigned_question_order(assessment)
    per_section = _group_attempts(attempts, aq_order)

    # ── Static sequence: DFS the tree, emitting each section's questions ──
    static_sequence = []
    for section in _walk_static(sections):
        static_sequence.extend(per_section.get(section.id, []))

    # ── Delivery sequence ──
    rng = random.Random(f"session-{session_id}")

    if assessment.display_order == "RANDOM":
        # Assessment-level random: shuffle the entire question set.
        delivered = list(static_sequence)
        rng.shuffle(delivered)
    else:
        delivered = []
        # Root sections always keep their configured order (issue 8: parent
        # levels are never randomized by a lower section's RANDOM setting).
        roots = [s for s in sections if s.parent_id is None]
        roots.sort(key=lambda s: (s.order, s.id))
        for root in roots:
            _emit_node(root, per_section, sections_by_id, rng, delivered)

    static_index = {id(att): i for i, att in enumerate(static_sequence)}
    return [(static_index.get(id(att), 0), att) for att in delivered]


def _emit_node(section, per_section, sections_by_id, rng, delivered):
    """Emit one section's direct questions, then its children's subtrees.

    At a section whose ``order_mode`` is RANDOM (Report 7 §8):
      - its child subsections are visited in SHUFFLED order
      - the questions directly under it are SHUFFLED
    At a STATIC section, everything keeps configured order.
    """
    is_random = section.order_mode == "RANDOM"

    direct = list(per_section.get(section.id, []))
    if is_random and len(direct) > 1:
        rng.shuffle(direct)
    delivered.extend(direct)

    children = _ordered_children(section.id, sections_by_id)
    if is_random and len(children) > 1:
        rng.shuffle(children)
    for child in children:
        _emit_node(child, per_section, sections_by_id, rng, delivered)


def section_display_path(section, sections):
    """Human-readable path of section titles root → leaf (Report 7 §3/§42)."""
    sections_by_id = {s.id: s for s in sections}
    path = []
    node = section
    while node is not None:
        path.append(node.title)
        node = sections_by_id.get(node.parent_id)
    path.reverse()
    return " > ".join(path)

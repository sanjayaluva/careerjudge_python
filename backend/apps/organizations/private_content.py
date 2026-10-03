"""Private content space of a Corporate Exclusive organization.

Report 9 #39-#47/#51/#52/#95 (1 Oct 2026): the Corporate Exclusive Admin
authors his organization's own question bank, assessments, reports and
training courses "in exclusive environment", and its members take / learn
them. Report 4 §3 (13 Aug 2026, p.7 and CJA Issue 15 p.38) sets who may see
that content: "No one, including CJ Admin, should have ACCESS to the exclusive
platform's contents", and the exclusive organization has no access to CJ's
question bank, reports or profiling solutions (CJ assessments and courses
reach it only through CJ Admin's licensing — Report 9 #97/#98).

The environment is a logical one: content roots (question-bank Category and
Question, Assessment, Report, TrainingCourse) carry ``owner_organization``;
NULL means CareerJudge content. The superuser keeps access for support.
"""

from rest_framework.exceptions import ValidationError

from .models import OrganizationMember

EXCLUSIVE_ORG_TYPE = "corp_exclusive"
PRIVATE_AUTHOR_ROLE = "corp_exclusive"


def _role(user) -> str | None:
    return user.role.name if getattr(user, "role", None) else None


def member_exclusive_org_ids(user) -> list[int]:
    """Corporate Exclusive organizations the user belongs to (any membership),
    first-joined first. Code review (3 Oct 2026): CareerJudge staff never
    count as members of one — tagging a CJ Admin, Trainer, … to an exclusive
    organization must not open its private content to him (Report 4 §3)."""
    from .scoping import is_cj_staff

    if not getattr(user, "is_authenticated", False) or is_cj_staff(user):
        return []
    return list(
        OrganizationMember.objects.filter(user=user, organization__type=EXCLUSIVE_ORG_TYPE)
        .order_by("joined_at", "id")
        .values_list("organization_id", flat=True)
    )


def is_private_author(user) -> bool:
    """The Corporate Exclusive Admin works in his organization's private space
    only (not in CJ's question bank / reports)."""
    return bool(
        getattr(user, "is_authenticated", False)
        and not user.is_superuser
        and _role(user) == PRIVATE_AUTHOR_ROLE
    )


def author_org_ids(user) -> list[int]:
    """Organizations whose private content ``user`` authors (empty if none)."""
    return member_exclusive_org_ids(user) if is_private_author(user) else []


def space_filter(qs, user, field: str = "owner_organization"):
    """Limit ``qs`` to the content space ``user`` works in: the superuser sees
    everything, a Corporate Exclusive Admin only his organization's private
    content, everyone else (CJ Admin and all CJ roles included) only CJ
    content."""
    if user.is_superuser:
        return qs
    if is_private_author(user):
        return qs.filter(**{f"{field}_id__in": author_org_ids(user)})
    return qs.filter(**{f"{field}__isnull": True})


def in_space(user, owner_id) -> bool:
    """Does content owned by ``owner_id`` (None = CJ) belong to ``user``'s space?"""
    if user.is_superuser:
        return True
    if is_private_author(user):
        return owner_id is not None and owner_id in author_org_ids(user)
    return owner_id is None


def can_author_private(user, owner_id) -> bool:
    """May ``user`` change private content owned by ``owner_id``? Its own
    organization's Corporate Exclusive Admin (and the superuser) only."""
    if owner_id is None:
        return False
    return user.is_superuser or owner_id in author_org_ids(user)


def resolve_owner_org_id(user, requested=None) -> int | None:
    """Owner for new content ``user`` creates: CJ (None) for everyone but a
    Corporate Exclusive Admin, whose content always belongs to one of his
    organizations — the one chosen in the UI (``requested``) or his first."""
    if not is_private_author(user):
        return None
    org_ids = author_org_ids(user)
    if not org_ids:
        raise ValidationError(
            {"owner_organization": "Your account is not tagged to an exclusive organization yet."}
        )
    if requested in (None, ""):
        return org_ids[0]
    try:
        requested = int(requested)
    except (TypeError, ValueError) as exc:
        raise ValidationError({"owner_organization": "Invalid organization."}) from exc
    if requested not in org_ids:
        raise ValidationError(
            {"owner_organization": "You can only add content to your own organization."}
        )
    return requested


def require_same_space(owner_id, other_owner_id, what: str) -> None:
    """Content of one space may only use content of the same space (a private
    assessment takes its own organization's questions, a CJ course CJ
    assessments, …)."""
    if owner_id != other_owner_id:
        raise ValidationError(
            {"detail": f"That {what} belongs to a different content space and cannot be used here."}
        )

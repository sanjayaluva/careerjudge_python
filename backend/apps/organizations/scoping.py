"""Organization scoping helpers (Corporate-Exclusive, Phase 1).

Logical multi-tenancy: one database, isolation by organization membership.
These helpers resolve the requesting user's organization(s) and the content
assigned to them, so corporate-facing querysets can be scoped to a single
corporate without leaking data across tenants.

A "corporate individual" is a plain individual user who belongs to a corporate
(``corporate`` / ``corp_exclusive``) organization and is NOT an org admin — i.e.
an employee who should only see the assessments/content their corporate was
assigned (CJ_UC030). Non-corporate users (individuals with no membership,
staff roles, admins) are never scoped by these helpers.
"""

from .models import OrganizationAssignment, OrganizationMember

CORPORATE_ORG_TYPES = ("corporate", "corp_exclusive")


def user_org_ids(user) -> list[int]:
    """Organization ids the user is a member of (empty for non-members)."""
    if not getattr(user, "is_authenticated", False):
        return []
    return list(
        OrganizationMember.objects.filter(user=user).values_list("organization_id", flat=True)
    )


def user_primary_organization(user):
    """The user's first organization membership's Organization, or None."""
    if not getattr(user, "is_authenticated", False):
        return None
    membership = (
        OrganizationMember.objects.filter(user=user)
        .select_related("organization")
        .order_by("joined_at")
        .first()
    )
    return membership.organization if membership else None


def is_corporate_individual(user) -> bool:
    """True when the user is a corporate EMPLOYEE (member, not admin).

    Such a user's content visibility is limited to what their corporate was
    assigned. Org admins (``is_admin``) and non-members return False.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    role_name = user.role.name if getattr(user, "role", None) else None
    if role_name != "individual":
        return False
    return OrganizationMember.objects.filter(
        user=user,
        is_admin=False,
        organization__type__in=CORPORATE_ORG_TYPES,
    ).exists()


def assigned_item_ids(user, item_type: str) -> set[int]:
    """Ids of items of ``item_type`` assigned to any of the user's orgs.

    ``item_type`` is one of ``OrganizationAssignment.ITEM_TYPE_CHOICES``
    (``assessment`` / ``training_course`` / ``counseling``).
    """
    org_ids = user_org_ids(user)
    if not org_ids:
        return set()
    return set(
        OrganizationAssignment.objects.filter(
            organization_id__in=org_ids, item_type=item_type
        ).values_list("item_id", flat=True)
    )

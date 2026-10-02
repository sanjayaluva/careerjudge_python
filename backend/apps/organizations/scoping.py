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

from .models import Group, OrganizationAssignment, OrganizationMember

CORPORATE_ORG_TYPES = ("corporate", "corp_exclusive")
# Report 9 #57/#102: content is licensed to channel-partner organizations too,
# and the users a channel partner adds (members of his organization) are
# limited to what was licensed, exactly like corporate employees.
LICENSED_ORG_TYPES = (*CORPORATE_ORG_TYPES, "channel_partner")
# Counselling is licensed per organization as an on/off service: a
# ``counseling`` OrganizationAssignment always carries this item id.
COUNSELING_LICENCE_ITEM_ID = 0


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


def is_licensed_member(user) -> bool:
    """True for a plain individual who belongs (not as admin) to a corporate,
    corp-exclusive or channel-partner organization (Report 9 #14/#52/#57/#102).

    Such a user sees only the content licensed to his organization."""
    if not getattr(user, "is_authenticated", False):
        return False
    if role_name(user) != "individual":
        return False
    return OrganizationMember.objects.filter(
        user=user, is_admin=False, organization__type__in=LICENSED_ORG_TYPES
    ).exists()


def is_licence_scoped(user) -> bool:
    """Members and managers of an organization work only with the content CJ
    Admin licensed to it; everyone else (staff, plain individuals) is not
    restricted by licensing."""
    return is_licensed_member(user) or is_org_manager(user)


def org_has_counseling(organization_id) -> bool:
    """Report 9 #101: is counselling licensed to this organization?"""
    return OrganizationAssignment.objects.filter(
        organization_id=organization_id, item_type="counseling"
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


# ---------------------------------------------------------------------------
# Organization MANAGERS (Report 9, 1 Oct 2026)
#
# Corp Admin, Corp Exclusive Admin, Group Admin and Channel Partner manage
# ONLY the organization(s) they are tagged to (User Details pp.3-5; Report 4).
# CJ staff (CJ Admin, superuser, …) are unrestricted. ``None`` from these
# helpers means "unrestricted"; a list (possibly empty) means "only these".
# ---------------------------------------------------------------------------

ORG_MANAGER_ROLES = ("corp_admin", "corp_exclusive", "group_admin", "channel_partner")

# Roles each manager may create or assign (Doc 9 §2.3; SRS CJ_UC043).
_CREATABLE_ROLES = {
    "corp_admin": ("individual", "group_admin"),
    "corp_exclusive": ("individual", "group_admin"),
    "group_admin": ("individual",),
    "channel_partner": ("individual",),
}


def role_name(user) -> str | None:
    return user.role.name if getattr(user, "role", None) else None


def is_cj_admin(user) -> bool:
    """CJ Admin or superuser — the only users who manage roles and licensing."""
    if not getattr(user, "is_authenticated", False):
        return False
    return bool(user.is_superuser or role_name(user) == "cj_admin")


def is_org_manager(user) -> bool:
    if not getattr(user, "is_authenticated", False) or user.is_superuser:
        return False
    return role_name(user) in ORG_MANAGER_ROLES


def managed_org_ids(user) -> list[int] | None:
    """Organizations an org manager may see/manage; ``None`` = unrestricted."""
    if not is_org_manager(user):
        return None
    return user_org_ids(user)


def descendant_group_ids(group_ids) -> list[int]:
    """All sub-groups (any depth) below ``group_ids``, excluding them."""
    seen = set(group_ids)
    found: list[int] = []
    frontier = list(group_ids)
    while frontier:
        children = [
            gid
            for gid in Group.objects.filter(parent_id__in=frontier).values_list("id", flat=True)
            if gid not in seen
        ]
        seen.update(children)
        found.extend(children)
        frontier = children
    return found


def own_group_ids(user) -> list[int]:
    """Groups a Group Admin is tagged to (his own group, not sub-groups)."""
    return list(
        OrganizationMember.objects.filter(user=user, group__isnull=False).values_list(
            "group_id", flat=True
        )
    )


def managed_group_ids(user) -> list[int] | None:
    """Group Admin tagged to a group is limited to that group and its
    sub-groups (Report 9 #23) — his own group(s) first; else ``None``."""
    if role_name(user) != "group_admin" or not is_org_manager(user):
        return None
    ids = own_group_ids(user)
    if not ids:
        return None
    return ids + descendant_group_ids(ids)


def group_admin_editable_group_ids(user) -> list[int]:
    """Groups a Group Admin may edit or delete: the sub-groups below his own
    group (never his own group itself — that is the Corp Admin's)."""
    return descendant_group_ids(own_group_ids(user))


def can_set_up_group_admins(user) -> bool:
    """Report 9 #21/#37/#4: CJ Admin and the organization's own admin (Corp
    Admin / Corp Exclusive Admin) define Group Admins and their rights."""
    return is_cj_admin(user) or role_name(user) in ("corp_admin", "corp_exclusive")


def report_member_ids_for_group_admin(user) -> list[int]:
    """Report 9 #27: members whose reports a Group Admin may view/download —
    those of the group(s) (and sub-groups) where his Corp Admin turned
    "Can view & download members' reports" on; otherwise none."""
    permitted = list(
        OrganizationMember.objects.filter(
            user=user, group__isnull=False, can_view_member_reports=True
        ).values_list("group_id", flat=True)
    )
    if not permitted:
        return []
    group_ids = permitted + descendant_group_ids(permitted)
    return list(
        OrganizationMember.objects.filter(group_id__in=group_ids).values_list("user_id", flat=True)
    )


def can_manage_org(user, organization_id) -> bool:
    org_ids = managed_org_ids(user)
    return org_ids is None or int(organization_id) in org_ids


def managed_user_ids(user) -> list[int] | None:
    """Users an org manager may see/manage: members of his organization(s)
    (of his group, for a Group Admin tagged to one). ``None`` = unrestricted."""
    org_ids = managed_org_ids(user)
    if org_ids is None:
        return None
    members = OrganizationMember.objects.filter(organization_id__in=org_ids)
    group_ids = managed_group_ids(user)
    if group_ids is not None:
        members = members.filter(group_id__in=group_ids)
    return list(members.values_list("user_id", flat=True))


def creatable_role_names(user) -> tuple[str, ...] | None:
    """Role names a manager may give to users he creates; ``None`` = any."""
    if not is_org_manager(user):
        return None
    return _CREATABLE_ROLES.get(role_name(user), ())

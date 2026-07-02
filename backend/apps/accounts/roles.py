"""Role-permissions registry for django-role-permissions.

Note: We primarily use our own Role/ModuleRight models for fine-grained
module-scoped RBAC (per UC018). django-role-permissions is wired for
compatibility with libraries that depend on it (e.g. some third-party
packages). The canonical source of truth for permissions is our ModuleRight
table.

SME vs Reviewer (split per client clarification 2026-06-30):
  - SME:      Creates / views / edits / deletes OWN questions (unreviewed).
  - Reviewer: Reviews questions, approves/rejects. No create/edit/delete.
"""

from rolepermissions.roles import AbstractUserRole


class CJAdmin(AbstractUserRole):
    available_permissions = ["*"]


class CorporateAdmin(AbstractUserRole):
    available_permissions = [
        "view_user",
        "add_user",
        "change_user",
        "view_organization",
    ]


class Individual(AbstractUserRole):
    available_permissions = [
        "view_self_profile",
        "change_self_profile",
        "take_assessment",
    ]


class Counsellor(AbstractUserRole):
    available_permissions = [
        "view_user",
        "view_assessment_result",
        "create_counseling_note",
    ]


class Trainer(AbstractUserRole):
    available_permissions = [
        "view_user",
        "view_training",
        "assign_training",
    ]


class Psychometrician(AbstractUserRole):
    available_permissions = [
        "view_question_bank",
        "add_question",
        "change_question",
        "review_question",
        "view_assessment_result",
    ]


class SME(AbstractUserRole):
    """Subject Matter Expert — creates/edits/deletes own questions (unreviewed)."""

    available_permissions = [
        "view_question_bank",
        "add_question",
        "change_question",
        "delete_question",
        "request_delete_question",
    ]


class Reviewer(AbstractUserRole):
    """Reviewer — reviews questions, approves/rejects. No create/edit/delete."""

    available_permissions = [
        "view_question_bank",
        "review_question",
        "approve_question",
        "reject_question",
    ]


class GroupAdmin(AbstractUserRole):
    available_permissions = [
        "view_user",
        "view_group",
        "assign_assessment",
    ]


class CorpExclusive(AbstractUserRole):
    available_permissions = [
        "view_user",
        "add_user",
        "view_organization",
    ]


class ChannelPartner(AbstractUserRole):
    """Channel Partner — manages own individual users + assessments."""

    available_permissions = [
        "view_user",
        "add_user",
        "change_user",
        "view_organization",
        "change_organization",
        "view_assessment",
        "add_assessment",
        "view_report",
        "generate_report",
    ]

"""Role-permissions registry for django-role-permissions.

Note: We primarily use our own Role/ModuleRight models for fine-grained
module-scoped RBAC (per UC018). django-role-permissions is wired for
compatibility with libraries that depend on it (e.g. some third-party
packages). The canonical source of truth for permissions is our ModuleRight
table.
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
        "view_assessment_result",
    ]


class SMEReviewer(AbstractUserRole):
    available_permissions = [
        "view_question_bank",
        "review_question",
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

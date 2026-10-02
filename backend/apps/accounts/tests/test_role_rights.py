"""Guards for the role-rights table and the module permission maps.

1. Every routed viewset action guarded by a ``HasModulePermission`` subclass
   must appear in that class's ``action_map`` — an unmapped action is refused
   for every non-superuser, which is how Profiling and Reports looked
   "unavailable" to the client (Report 9 #89/#90/#118/#119).
2. The latest sync migration's frozen table must equal ``ROLE_PERMISSIONS``.
3. Syncing removes stale rights from system roles and leaves custom roles alone.
"""

import importlib

import pytest
from django.urls import URLPattern, URLResolver, get_resolver

from apps.accounts.models import ModuleRight, Role
from apps.accounts.role_rights import ROLE_PERMISSIONS, sync_role_rights
from core.permissions import HasModulePermission

LATEST_SYNC_MIGRATION = "apps.accounts.migrations.0015_sync_system_role_rights"


def _iter_patterns(patterns):
    for p in patterns:
        if isinstance(p, URLResolver):
            yield from _iter_patterns(p.url_patterns)
        elif isinstance(p, URLPattern):
            yield p


def _module_permission_gaps():
    gaps = []
    for pattern in _iter_patterns(get_resolver().url_patterns):
        callback = pattern.callback
        view_cls = getattr(callback, "cls", None)
        actions = getattr(callback, "actions", None)
        if view_cls is None or not actions:
            continue
        for perm_cls in getattr(view_cls, "permission_classes", []):
            if not (isinstance(perm_cls, type) and issubclass(perm_cls, HasModulePermission)):
                continue
            for method, action in actions.items():
                entry = perm_cls.action_map.get(action)
                if isinstance(entry, dict):
                    entry = entry.get(method.upper())
                if entry is None:
                    gaps.append(f"{view_cls.__name__}.{action} [{method.upper()}]")
    return sorted(set(gaps))


def test_every_routed_action_has_a_module_right():
    assert _module_permission_gaps() == []


def test_latest_sync_migration_matches_table():
    migration = importlib.import_module(LATEST_SYNC_MIGRATION)
    assert migration.ROLE_PERMISSIONS == ROLE_PERMISSIONS


@pytest.mark.django_db
def test_sync_adds_missing_and_removes_stale_rights():
    counsellor = Role.objects.create(name="counsellor", is_system=True, is_frozen=True)
    ModuleRight.objects.create(role=counsellor, module="assessment", action="view")
    ModuleRight.objects.create(role=counsellor, module="reporting", action="view")
    custom = Role.objects.create(name="Senior Counsellor", is_system=False, is_frozen=False)
    ModuleRight.objects.create(role=custom, module="assessment", action="view")

    sync_role_rights(Role, ModuleRight, ROLE_PERMISSIONS)

    rights = set(ModuleRight.objects.filter(role=counsellor).values_list("module", "action"))
    assert rights == set(ROLE_PERMISSIONS["counsellor"])
    assert ("assessment", "view") not in rights
    assert ModuleRight.objects.filter(role=custom, module="assessment").exists()


def test_profiling_and_reporting_creators():
    for role in ("cj_admin", "psychometrician"):
        rights = set(ROLE_PERMISSIONS[role])
        assert ("career_profiling", "add") in rights
        assert ("reporting", "add") in rights
        assert ("reporting", "change") in rights

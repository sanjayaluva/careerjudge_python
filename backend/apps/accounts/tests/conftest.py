"""Shared pytest fixtures for accounts tests."""

import pytest
from rest_framework.test import APIClient

from apps.accounts.services import get_or_create_default_roles

from .factories import UserFactory


@pytest.fixture
def client():
    """Unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def roles(db):
    """Ensure the 9 default roles exist."""
    return get_or_create_default_roles()


@pytest.fixture
def cj_admin_role(roles):
    return roles["cj_admin"]


@pytest.fixture
def individual_role(roles):
    return roles["individual"]


@pytest.fixture
def cj_admin_user(db, cj_admin_role):
    """A CJ Admin user with full permissions."""
    # ensure admin role has the right to view/add/change/delete accounts users
    from apps.accounts.models import ModuleRight

    for action in ("view", "add", "change", "delete"):
        ModuleRight.objects.get_or_create(role=cj_admin_role, module="accounts", action=action)
    user = UserFactory(role=cj_admin_role, email="admin@test.com")
    return user


@pytest.fixture
def individual_user(db, individual_role):
    return UserFactory(role=individual_role, email="individual@test.com")


@pytest.fixture
def authed_client(client, cj_admin_user):
    """DRF client authenticated as a CJ Admin."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(cj_admin_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


@pytest.fixture
def individual_client(client, individual_user):
    """DRF client authenticated as an individual user."""
    from rest_framework_simplejwt.tokens import RefreshToken

    refresh = RefreshToken.for_user(individual_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client

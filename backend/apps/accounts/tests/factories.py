"""Test factories for accounts module.

Uses factory_boy. Each factory creates a model instance with sensible defaults
for tests. Combine with pytest fixtures for clean test code.
"""

import factory
from factory.django import DjangoModelFactory

from apps.accounts.models import (
    EmailVerificationToken,
    ModuleRight,
    PasswordResetToken,
    Role,
    User,
    UserProfile,
)


class RoleFactory(DjangoModelFactory):
    class Meta:
        model = Role

    name = factory.Sequence(lambda n: f"role_{n}")
    description = factory.Faker("sentence")
    is_frozen = False


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@test.com")
    full_name = factory.Faker("name")
    is_active = True
    is_email_verified = True
    is_trial_user = False
    role = factory.SubFactory(RoleFactory, name="individual")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        raw_password = extracted or "TestP@ssw0rd123"
        self.set_password(raw_password)
        self.save()
        self._raw_password = raw_password


class UserProfileFactory(DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    gender = "male"
    mobile = "+1234567890"
    bio = factory.Faker("sentence")


class EmailVerificationTokenFactory(DjangoModelFactory):
    class Meta:
        model = EmailVerificationToken

    user = factory.SubFactory(UserFactory)


class PasswordResetTokenFactory(DjangoModelFactory):
    class Meta:
        model = PasswordResetToken

    user = factory.SubFactory(UserFactory)


class ModuleRightFactory(DjangoModelFactory):
    class Meta:
        model = ModuleRight

    role = factory.SubFactory(RoleFactory)
    module = "accounts"
    action = "view"

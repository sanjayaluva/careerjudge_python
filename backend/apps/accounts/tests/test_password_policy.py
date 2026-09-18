"""E-SRS-1: password policy validators (special char + no leading digit)."""

import pytest
from django.core.exceptions import ValidationError

from apps.accounts.validators import NoLeadingDigitValidator, SpecialCharacterValidator


class TestSpecialCharacterValidator:
    def test_rejects_alphanumeric_only(self):
        with pytest.raises(ValidationError):
            SpecialCharacterValidator().validate("Password1")

    def test_accepts_with_special(self):
        SpecialCharacterValidator().validate("Password1!")  # no raise


class TestNoLeadingDigitValidator:
    def test_rejects_leading_digit(self):
        with pytest.raises(ValidationError):
            NoLeadingDigitValidator().validate("1Password!")

    def test_accepts_leading_letter(self):
        NoLeadingDigitValidator().validate("Password1!")  # no raise

    def test_accepts_leading_special(self):
        NoLeadingDigitValidator().validate("!Password1")  # no raise


@pytest.mark.django_db
def test_validate_password_enforces_policy():
    """The validators are wired into AUTH_PASSWORD_VALIDATORS."""
    from django.contrib.auth.password_validation import validate_password

    with pytest.raises(ValidationError):
        validate_password("Passw0rdNoSpecial")  # missing special char
    with pytest.raises(ValidationError):
        validate_password("1Password!")  # leading digit
    # A compliant password passes.
    validate_password("Str0ng!Pass")

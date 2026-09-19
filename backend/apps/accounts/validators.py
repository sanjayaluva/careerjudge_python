"""Custom password validators (E-SRS-1).

The dossier's elective password policy requires that a password:
  - contains at least one special (non-alphanumeric) character, and
  - does not start with a numeric digit.

These plug into Django's AUTH_PASSWORD_VALIDATORS, so they run everywhere
`validate_password` is called (signup, email-verification set-password,
password reset, admin-set passwords).
"""

import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

_SPECIAL_RE = re.compile(r"[^A-Za-z0-9]")


class SpecialCharacterValidator:
    """Require at least one special (non-alphanumeric) character."""

    def validate(self, password, user=None):
        if not _SPECIAL_RE.search(password or ""):
            raise ValidationError(
                _("Password must contain at least one special character."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _("Your password must contain at least one special character.")


class NoLeadingDigitValidator:
    """Reject passwords that start with a numeric digit."""

    def validate(self, password, user=None):
        if password and password[0].isdigit():
            raise ValidationError(
                _("Password must not start with a number."),
                code="password_leading_digit",
            )

    def get_help_text(self):
        return _("Your password must not start with a number.")

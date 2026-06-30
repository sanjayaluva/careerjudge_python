"""App config for Question Bank."""

from django.apps import AppConfig


class QuestionBankConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.question_bank"
    verbose_name = "Question Bank"
    description = "21 question types, tests, sections, media"

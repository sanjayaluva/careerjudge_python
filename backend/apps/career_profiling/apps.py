"""App config for Career Profiling."""
from django.apps import AppConfig


class CareerProfilingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.career_profiling"
    verbose_name = "Career Profiling"
    description = "Profiling config, match index, gap values"

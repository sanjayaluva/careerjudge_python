"""URL routes for the Assessment module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssessmentModificationRequestViewSet,
    AssessmentQuestionViewSet,
    AssessmentSectionViewSet,
    AssessmentViewSet,
    PsychometricGroupViewSet,
    SessionViewSet,
)

app_name = "assessment"

# Register the assessment router first. We CANNOT register 'assessments/sessions'
# on the same DefaultRouter because the 'assessments' prefix's <pk> pattern
# would shadow it (treating 'sessions' as a pk). Instead, we register the
# SessionViewSet on a separate router and include it FIRST in urlpatterns
# so its more-specific pattern wins.
router = DefaultRouter()
router.register("assessments", AssessmentViewSet, basename="assessment")
# SRS 03_assessment_configuration.json §2.2/§2.3
router.register(
    "assessment-modification-requests",
    AssessmentModificationRequestViewSet,
    basename="assessment-modification-request",
)

session_router = DefaultRouter()
session_router.register("assessments/sessions", SessionViewSet, basename="session")

# Nested routes for sections and questions within an assessment
section_router = DefaultRouter()
section_router.register("sections", AssessmentSectionViewSet, basename="section")

question_router = DefaultRouter()
question_router.register("questions", AssessmentQuestionViewSet, basename="question")

# PSY-A1: psychometric groups nested under an assessment
psych_router = DefaultRouter()
psych_router.register(
    "psychometric-groups", PsychometricGroupViewSet, basename="psychometric-group"
)

urlpatterns = [
    # Session routes — included FIRST so /api/assessments/sessions/ matches
    # before /api/assessments/<pk>/ (which would treat 'sessions' as a pk).
    path("", include(session_router.urls)),
    path("", include(router.urls)),
    # Assessment sections (nested under assessment)
    path(
        "assessments/<int:assessment_id>/",
        include(section_router.urls),
    ),
    # Psychometric groups (nested under assessment) — PSY-A1
    path(
        "assessments/<int:assessment_id>/",
        include(psych_router.urls),
    ),
    # Assessment questions (nested under section)
    path(
        "assessments/<int:assessment_id>/sections/<int:section_id>/",
        include(question_router.urls),
    ),
]

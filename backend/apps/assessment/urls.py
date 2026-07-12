"""URL routes for the Assessment module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AssessmentQuestionViewSet,
    AssessmentSectionViewSet,
    AssessmentViewSet,
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

session_router = DefaultRouter()
session_router.register("assessments/sessions", SessionViewSet, basename="session")

# Nested routes for sections and questions within an assessment
section_router = DefaultRouter()
section_router.register("sections", AssessmentSectionViewSet, basename="section")

question_router = DefaultRouter()
question_router.register("questions", AssessmentQuestionViewSet, basename="question")

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
    # Assessment questions (nested under section)
    path(
        "assessments/<int:assessment_id>/sections/<int:section_id>/",
        include(question_router.urls),
    ),
]

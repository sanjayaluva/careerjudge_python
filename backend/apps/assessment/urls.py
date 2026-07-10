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

router = DefaultRouter()
router.register("assessments", AssessmentViewSet, basename="assessment")
router.register("assessments/sessions", SessionViewSet, basename="session")

# Nested routes for sections and questions within an assessment
section_router = DefaultRouter()
section_router.register("sections", AssessmentSectionViewSet, basename="section")

question_router = DefaultRouter()
question_router.register("questions", AssessmentQuestionViewSet, basename="question")

urlpatterns = [
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

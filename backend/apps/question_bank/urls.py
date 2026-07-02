"""URL routes for the question_bank module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    QuestionReviewListView,
    QuestionReviewView,
    QuestionViewSet,
)

app_name = "question_bank"

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("questions", QuestionViewSet, basename="question")

urlpatterns = [
    path("", include(router.urls)),
    # Question review workflow (UC014, UC015)
    path(
        "questions/<int:question_id>/review/",
        QuestionReviewView.as_view(),
        name="question-review",
    ),
    path(
        "questions/<int:question_id>/reviews/",
        QuestionReviewListView.as_view(),
        name="question-reviews-list",
    ),
]

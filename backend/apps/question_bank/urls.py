"""URL routes for the question_bank module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CategoryViewSet,
    QuestionReviewListView,
    QuestionReviewView,
    QuestionViewSet,
)
from .views_children import (
    BulkOptionsView,
    FlashItemViewSet,
    HotspotAreaViewSet,
    MediaFileViewSet,
    ResponseOptionViewSet,
)

app_name = "question_bank"

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("questions", QuestionViewSet, basename="question")

# Nested routers for child resources under questions
question_router = DefaultRouter()
question_router.register("options", ResponseOptionViewSet, basename="question-options")
question_router.register("media", MediaFileViewSet, basename="question-media")
question_router.register("flash-items", FlashItemViewSet, basename="question-flash")
question_router.register("hotspots", HotspotAreaViewSet, basename="question-hotspots")

urlpatterns = [
    path("", include(router.urls)),
    # Question review workflow
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
    # Bulk save options
    path(
        "questions/<int:question_id>/options/bulk/",
        BulkOptionsView.as_view(),
        name="question-options-bulk",
    ),
    # Nested child resource routes
    path(
        "questions/<int:question_id>/",
        include(question_router.urls),
    ),
]

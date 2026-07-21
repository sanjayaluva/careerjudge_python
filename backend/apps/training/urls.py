"""URL routes for the Training module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CourseAssessmentViewSet,
    CourseLessonViewSet,
    CourseRegistrationViewSet,
    LessonTopicViewSet,
    LiveSessionViewSet,
    SessionContentViewSet,
    TopicSessionViewSet,
    TrainingCategoryViewSet,
    TrainingCourseViewSet,
)

app_name = "training"

router = DefaultRouter()
router.register("categories", TrainingCategoryViewSet, basename="category")
router.register("courses", TrainingCourseViewSet, basename="course")
router.register("registrations", CourseRegistrationViewSet, basename="registration")
router.register("lessons", CourseLessonViewSet, basename="lesson")
router.register("topics", LessonTopicViewSet, basename="topic")
router.register("sessions", TopicSessionViewSet, basename="session")
router.register("contents", SessionContentViewSet, basename="content")
router.register("course-assessments", CourseAssessmentViewSet, basename="course-assessment")
router.register("live-sessions", LiveSessionViewSet, basename="live-session")

urlpatterns = [
    path("", include(router.urls)),
]

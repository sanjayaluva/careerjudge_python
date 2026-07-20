"""URL routes for the Training module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CourseLessonViewSet,
    CourseRegistrationViewSet,
    LessonTopicViewSet,
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

urlpatterns = [
    path("", include(router.urls)),
]

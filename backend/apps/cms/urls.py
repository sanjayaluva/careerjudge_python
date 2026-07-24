"""URL routes for the CMS module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BannerViewSet, MenuItemViewSet, PageViewSet

app_name = "cms"

router = DefaultRouter()
router.register("pages", PageViewSet, basename="page")
router.register("banners", BannerViewSet, basename="banner")
router.register("menu", MenuItemViewSet, basename="menu-item")

urlpatterns = [
    path("", include(router.urls)),
]

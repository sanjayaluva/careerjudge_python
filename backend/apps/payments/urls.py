"""URL routes for the Payments module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, stripe_webhook

app_name = "payments"

router = DefaultRouter()
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("", include(router.urls)),
    path("stripe-webhook/", stripe_webhook, name="stripe-webhook"),
]

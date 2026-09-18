"""URL routes for the Payments module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PaymentViewSet, razorpay_webhook, stripe_webhook

app_name = "payments"

router = DefaultRouter()
router.register("", PaymentViewSet, basename="payment")

urlpatterns = [
    path("stripe-webhook/", stripe_webhook, name="stripe-webhook"),
    path("razorpay-webhook/", razorpay_webhook, name="razorpay-webhook"),
    path("", include(router.urls)),
]

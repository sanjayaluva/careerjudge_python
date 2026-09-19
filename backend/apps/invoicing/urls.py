"""URL routes for the Invoicing module."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InvoiceItemViewSet, InvoiceViewSet

app_name = "invoicing"

router = DefaultRouter()
router.register("invoices", InvoiceViewSet, basename="invoice")
router.register("invoice-items", InvoiceItemViewSet, basename="invoice-item")

urlpatterns = [
    path("", include(router.urls)),
]

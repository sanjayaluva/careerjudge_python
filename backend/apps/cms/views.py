"""Views for the CMS module.

Endpoints:
  GET/POST  /api/cms/pages/            — list/create pages
  GET/PATCH /api/cms/pages/<id>/       — retrieve/update page
  DELETE    /api/cms/pages/<id>/       — delete page
  GET       /api/cms/pages/slug/<slug>/— retrieve published page by slug
  GET/POST  /api/cms/banners/          — list/create banners
  GET/PATCH /api/cms/banners/<id>/     — retrieve/update banner
  DELETE    /api/cms/banners/<id>/     — delete banner
  GET/POST  /api/cms/menu/             — list/create menu items
  GET/PATCH /api/cms/menu/<id>/        — retrieve/update menu item
  DELETE    /api/cms/menu/<id>/        — delete menu item
"""

from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.mixins import ActionSerializerMixin
from core.permissions import HasModulePermission

from .models import Banner, MenuItem, Page
from .serializers import (
    BannerSerializer,
    MenuItemSerializer,
    PageListSerializer,
    PageSerializer,
)


class HasCMSPermission(HasModulePermission):
    module = "cms"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
        "by_slug": "view",
    }


class PageViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for CMS pages."""

    queryset = Page.objects.select_related("created_by").all()
    permission_classes = [IsAuthenticated, HasCMSPermission]
    serializer_class = PageSerializer
    serializer_classes = {"list": PageListSerializer}
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "slug", "body"]
    ordering_fields = ["order", "title", "created_at", "updated_at"]
    ordering = ["order", "title"]

    def get_queryset(self):
        qs = super().get_queryset()
        if status_filter := self.request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {"message": "OK", "data": self.get_serializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Page created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Page updated.", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="slug/(?P<slug>[^/]+)")
    def by_slug(self, request, slug=None):
        """Retrieve a published page by its slug (public endpoint)."""
        page = Page.objects.filter(slug=slug, status="published").first()
        if not page:
            return Response(
                {"error": {"code": "not_found", "message": "Page not found."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"message": "OK", "data": PageSerializer(page).data},
            status=status.HTTP_200_OK,
        )


class BannerViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for CMS banners."""

    queryset = Banner.objects.select_related("created_by").all()
    permission_classes = [IsAuthenticated, HasCMSPermission]
    serializer_class = BannerSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["title", "subtitle", "body"]
    ordering_fields = ["order", "created_at"]
    ordering = ["order", "-created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if active := self.request.query_params.get("active"):
            qs = qs.filter(is_active=active == "true")
        if position := self.request.query_params.get("position"):
            qs = qs.filter(position=position)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {"message": "OK", "data": self.get_serializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Banner created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Banner updated.", "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class MenuItemViewSet(ModelViewSet):
    """CRUD for CMS menu items."""

    queryset = MenuItem.objects.all()
    permission_classes = [IsAuthenticated, HasCMSPermission]
    serializer_class = MenuItemSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["location", "order"]
    ordering = ["location", "order"]

    def get_queryset(self):
        qs = super().get_queryset()
        if location := self.request.query_params.get("location"):
            qs = qs.filter(location=location)
        return qs

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {"message": "OK", "data": self.get_serializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Menu item created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

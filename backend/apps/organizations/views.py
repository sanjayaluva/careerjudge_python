"""Views for the organizations module."""

from django.shortcuts import get_object_or_404
from rest_framework import filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.mixins import ActionSerializerMixin
from core.permissions import HasModulePermission

from .models import Group, Organization, OrganizationMember
from .serializers import (
    GroupSerializer,
    OrganizationListSerializer,
    OrganizationMemberSerializer,
    OrganizationSerializer,
)


class HasOrganizationsPermission(HasModulePermission):
    module = "organizations"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
    }


class OrganizationViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for organizations.

    GET    /api/organizations/
    POST   /api/organizations/
    GET    /api/organizations/<id>/
    PATCH  /api/organizations/<id>/
    DELETE /api/organizations/<id>/
    """

    queryset = Organization.objects.all()
    permission_classes = [IsAuthenticated, HasOrganizationsPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "contact_email", "city", "country"]
    ordering_fields = ["created_at", "name", "type"]
    ordering = ["-created_at"]

    serializer_class = OrganizationSerializer
    serializer_classes = {
        "list": OrganizationListSerializer,
    }

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response(
            {"message": "OK", "data": resp.data},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"message": "OK", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        return Response(
            {
                "message": "Organization created.",
                "data": OrganizationSerializer(org).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        org = serializer.save()
        return Response(
            {
                "message": "Organization updated.",
                "data": OrganizationSerializer(org).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Organization deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )


class GroupViewSet(ActionSerializerMixin, ModelViewSet):
    """CRUD for groups within an organization.

    GET    /api/organizations/<org_id>/groups/
    POST   /api/organizations/<org_id>/groups/
    GET    /api/organizations/<org_id>/groups/<id>/
    PATCH  /api/organizations/<org_id>/groups/<id>/
    DELETE /api/organizations/<org_id>/groups/<id>/
    """

    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, HasOrganizationsPermission]

    def get_queryset(self):
        org_id = self.kwargs.get("organization_id")
        return Group.objects.filter(organization_id=org_id)

    def perform_create(self, serializer):
        org_id = self.kwargs.get("organization_id")
        org = get_object_or_404(Organization, id=org_id)
        serializer.save(organization=org)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response(
            {"message": "OK", "data": resp.data},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"message": "OK", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Group created.",
                "data": GroupSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(
            {
                "message": "Group updated.",
                "data": GroupSerializer(group).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Group deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )


class OrganizationMemberViewSet(ModelViewSet):
    """CRUD for organization members.

    GET    /api/organizations/<org_id>/members/
    POST   /api/organizations/<org_id>/members/         (add member by email)
    DELETE /api/organizations/<org_id>/members/<id>/
    PATCH  /api/organizations/<org_id>/members/<id>/    (update group/is_admin)
    """

    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsAuthenticated, HasOrganizationsPermission]

    def get_queryset(self):
        org_id = self.kwargs.get("organization_id")
        return OrganizationMember.objects.filter(organization_id=org_id).select_related(
            "user", "group"
        )

    def perform_create(self, serializer):
        org_id = self.kwargs.get("organization_id")
        org = get_object_or_404(Organization, id=org_id)
        serializer.save(organization=org)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response(
            {"message": "OK", "data": resp.data},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(
            {"message": "OK", "data": serializer.data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Member added.",
                "data": OrganizationMemberSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        kwargs.pop("partial", False)
        instance = self.get_object()
        # Handle group_id and is_admin updates
        group_id = request.data.get("group_id")
        is_admin = request.data.get("is_admin")
        if group_id is not None:
            instance.group_id = group_id if group_id else None
        if is_admin is not None:
            instance.is_admin = is_admin
        instance.save()
        return Response(
            {
                "message": "Member updated.",
                "data": OrganizationMemberSerializer(instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Member removed.", "data": {}},
            status=status.HTTP_200_OK,
        )

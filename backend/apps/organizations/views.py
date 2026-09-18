"""Views for the organizations module."""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from rest_framework import filters, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.mixins import ActionSerializerMixin
from core.permissions import HasModulePermission

from .models import (
    AssessmentSchedule,
    CorporateWebsite,
    Group,
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)
from .serializers import (
    AssessmentScheduleSerializer,
    CorporateWebsiteSerializer,
    GroupSerializer,
    OrganizationAssignmentSerializer,
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


class OrganizationAssignmentViewSet(ModelViewSet):
    """Assign published content to an organization (CJ_UC030, Doc 4).

    GET    /api/organizations/<org_id>/assignments/
    POST   /api/organizations/<org_id>/assignments/     (assign assessment/training/counseling)
    DELETE /api/organizations/<org_id>/assignments/<id>/

    Only org managers (organizations.add/change) may assign; the org's corporate
    individuals then see only the assessments assigned here (see
    ``apps.organizations.scoping``).
    """

    serializer_class = OrganizationAssignmentSerializer
    permission_classes = [IsAuthenticated, HasOrganizationsPermission]

    def get_queryset(self):
        org_id = self.kwargs.get("organization_id")
        return OrganizationAssignment.objects.filter(organization_id=org_id).select_related(
            "assigned_by"
        )

    def perform_create(self, serializer):
        org_id = self.kwargs.get("organization_id")
        org = get_object_or_404(Organization, id=org_id)
        serializer.save(organization=org, assigned_by=self.request.user)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        org_id = self.kwargs.get("organization_id")
        if OrganizationAssignment.objects.filter(
            organization_id=org_id,
            item_type=serializer.validated_data["item_type"],
            item_id=serializer.validated_data["item_id"],
        ).exists():
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "This item is already assigned to the organization.",
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        self.perform_create(serializer)
        return Response(
            {"message": "Item assigned.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Assignment removed.", "data": {}},
            status=status.HTTP_200_OK,
        )


class AssessmentScheduleViewSet(ModelViewSet):
    """CJ_UC053 — schedule an assessment for a corporate's employees + notify.

    GET    /api/organizations/<org_id>/schedules/
    POST   /api/organizations/<org_id>/schedules/
    DELETE /api/organizations/<org_id>/schedules/<id>/
    """

    serializer_class = AssessmentScheduleSerializer
    permission_classes = [IsAuthenticated, HasOrganizationsPermission]

    def get_queryset(self):
        org_id = self.kwargs.get("organization_id")
        return AssessmentSchedule.objects.filter(organization_id=org_id).select_related(
            "assessment", "group"
        )

    def perform_create(self, serializer):
        org_id = self.kwargs.get("organization_id")
        org = get_object_or_404(Organization, id=org_id)
        schedule = serializer.save(organization=org, created_by=self.request.user)
        self._notify_members(schedule)

    def _notify_members(self, schedule):
        from apps.notifications.models import notify_user

        members = OrganizationMember.objects.filter(
            organization=schedule.organization
        ).select_related("user")
        if schedule.group_id:
            members = members.filter(group_id=schedule.group_id)
        title = "Assessment scheduled"
        when = timezone.localtime(schedule.scheduled_at).strftime("%d %b %Y, %H:%M")
        body = f"'{schedule.assessment.title}' is scheduled for {when}."
        for m in members:
            if m.is_admin:
                continue
            notify_user(m.user, title, body, "assessment", "/assessments")
        schedule.notified = True
        schedule.save(update_fields=["notified"])

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Assessment scheduled and members notified.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Schedule removed.", "data": {}}, status=status.HTTP_200_OK)


class CorporateWebsiteViewSet(ModelViewSet):
    """CJ_UC054/UC055 — a corporate's branded portal (single, per organization).

    GET    /api/organizations/<org_id>/website/       (retrieve, 404 if none)
    POST   /api/organizations/<org_id>/website/       (create + generate admin)
    PATCH  /api/organizations/<org_id>/website/       (customize: layout/logo/color)
    """

    serializer_class = CorporateWebsiteSerializer
    permission_classes = [IsAuthenticated, HasOrganizationsPermission]

    def _org(self):
        return get_object_or_404(Organization, id=self.kwargs.get("organization_id"))

    def retrieve(self, request, *args, **kwargs):
        org = self._org()
        website = getattr(org, "corporate_website", None)
        if website is None:
            return Response({"message": "OK", "data": None}, status=status.HTTP_200_OK)
        return Response(
            {"message": "OK", "data": CorporateWebsiteSerializer(website).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        org = self._org()
        if getattr(org, "corporate_website", None) is not None:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "This organization already has a website.",
                        "details": {},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company_name = serializer.validated_data.get("company_name") or org.name
        slug = self._unique_slug(company_name or org.name)

        # CJ_UC055: generate a corporate-admin account + credentials.
        admin_user, temp_password = self._provision_admin(
            org, request.data.get("admin_email"), slug
        )

        website = CorporateWebsite.objects.create(
            organization=org,
            slug=slug,
            company_name=company_name,
            logo_url=serializer.validated_data.get("logo_url", ""),
            layout=serializer.validated_data.get("layout", "classic"),
            primary_color=serializer.validated_data.get("primary_color", "#4f46e5"),
            admin_user=admin_user,
        )
        data = CorporateWebsiteSerializer(website).data
        # Return the generated credentials exactly ONCE (never stored in plain text).
        if admin_user is not None and temp_password:
            data["generated_credentials"] = {
                "email": admin_user.email,
                "temporary_password": temp_password,
            }
        return Response(
            {"message": "Website created.", "data": data},
            status=status.HTTP_201_CREATED,
        )

    def partial_update(self, request, *args, **kwargs):
        org = self._org()
        website = getattr(org, "corporate_website", None)
        if website is None:
            return Response(
                {
                    "error": {
                        "code": "not_found",
                        "message": "No website for this organization.",
                        "details": {},
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        for field in ("company_name", "logo_url", "layout", "primary_color", "is_active"):
            if field in request.data:
                setattr(website, field, request.data[field])
        website.save()
        return Response(
            {"message": "Website updated.", "data": CorporateWebsiteSerializer(website).data},
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _unique_slug(base: str) -> str:
        root = slugify(base)[:50] or "corporate"
        slug = root
        n = 1
        while CorporateWebsite.objects.filter(slug=slug).exists():
            n += 1
            slug = f"{root}-{n}"
        return slug

    @staticmethod
    def _provision_admin(org, admin_email, slug):
        from apps.accounts.models import Role, User, UserProfile

        email = (admin_email or f"admin@{slug}.careerjudge").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            # Reuse an existing account (don't clobber); no new password issued.
            return User.objects.get(email__iexact=email), None
        role = Role.objects.filter(name="corp_admin").first()
        temp_password = get_random_string(length=12)
        admin = User.objects.create_user(
            email=email,
            password=temp_password,
            full_name=f"{org.name} Admin",
            is_active=True,
            is_email_verified=True,
            role=role,
        )
        UserProfile.objects.get_or_create(user=admin)
        OrganizationMember.objects.get_or_create(
            organization=org, user=admin, defaults={"is_admin": True}
        )
        return admin, temp_password


class CorporateSitePublicView(APIView):
    """Public tenant branding by slug (CJ_UC054) — for rendering a corporate's
    branded portal. No auth: only non-sensitive branding is exposed.

    GET /api/organizations/site/<slug>/
    """

    permission_classes = [AllowAny]

    def get(self, request, slug):
        website = CorporateWebsite.objects.filter(slug=slug, is_active=True).first()
        if website is None:
            return Response(
                {"error": {"code": "not_found", "message": "Site not found.", "details": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {
                "message": "OK",
                "data": {
                    "organization_id": website.organization_id,
                    "slug": website.slug,
                    "company_name": website.company_name,
                    "logo_url": website.logo_url,
                    "layout": website.layout,
                    "primary_color": website.primary_color,
                },
            },
            status=status.HTTP_200_OK,
        )

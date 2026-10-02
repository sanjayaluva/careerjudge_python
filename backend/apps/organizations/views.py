"""Views for the organizations module."""

import mimetypes

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from rest_framework import filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
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
from .scoping import (
    CORPORATE_ORG_TYPES,
    can_manage_org,
    can_set_up_group_admins,
    descendant_group_ids,
    group_admin_editable_group_ids,
    is_cj_admin,
    managed_group_ids,
    managed_org_ids,
    role_name,
)
from .serializers import (
    AssessmentScheduleSerializer,
    CorporateWebsiteSerializer,
    GroupAdminCreateSerializer,
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
        "my_access": "view",
    }


class HasOrgContentPermission(HasModulePermission):
    """Routes INSIDE an organization (groups, members, schedules, website):
    adding or changing them is managing that organization ('change'), not
    creating a new organization ('add')."""

    module = "organizations"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "change",
        "update": "change",
        "partial_update": "change",
        "destroy": "change",
        "create_group_admin": "change",
    }


class ManagedOrgMixin:
    """Nested organization routes: an organization manager (Corp Admin, Corp
    Exclusive, Group Admin, Channel Partner) reaches only his own
    organization's groups, members, schedules and website (Report 9 #1/#54)."""

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        org_id = self.kwargs.get("organization_id")
        if org_id is not None and not can_manage_org(request.user, org_id):
            raise NotFound("Organization not found.")


def _as_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _require_cj_admin(request, message):
    if not is_cj_admin(request.user):
        raise PermissionDenied(message)


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

    def get_queryset(self):
        # Report 9 #1/#3/#22/#54: managers see only their own organization(s).
        qs = super().get_queryset()
        org_ids = managed_org_ids(self.request.user)
        if org_ids is not None:
            qs = qs.filter(id__in=org_ids)
        return qs

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
        # Doc 9 §2.2: the organization record itself is CJ Admin's.
        _require_cj_admin(request, "Only CJ Admin can edit organization details.")
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

    @action(detail=False, methods=["get"], url_path="my-access")
    def my_access(self, request):
        """GET /api/organizations/my-access/ — the requester's own Group Admin
        set-up: his group(s) and whether his Corp Admin let him view and
        download his members' reports (Report 9 #27)."""
        user = request.user
        is_group_admin = role_name(user) == "group_admin"
        memberships = OrganizationMember.objects.filter(user=user)
        return Response(
            {
                "message": "OK",
                "data": {
                    "is_group_admin": is_group_admin,
                    "organization_ids": list(memberships.values_list("organization_id", flat=True)),
                    "group_ids": list(
                        memberships.filter(group__isnull=False).values_list("group_id", flat=True)
                    ),
                    "can_view_member_reports": is_group_admin
                    and memberships.filter(
                        group__isnull=False, can_view_member_reports=True
                    ).exists(),
                },
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        _require_cj_admin(request, "Only CJ Admin can delete an organization.")
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Organization deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )


class GroupViewSet(ManagedOrgMixin, ActionSerializerMixin, ModelViewSet):
    """CRUD for groups within an organization.

    GET    /api/organizations/<org_id>/groups/
    POST   /api/organizations/<org_id>/groups/
    GET    /api/organizations/<org_id>/groups/<id>/
    PATCH  /api/organizations/<org_id>/groups/<id>/
    DELETE /api/organizations/<org_id>/groups/<id>/
    """

    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated, HasOrgContentPermission]

    def get_queryset(self):
        org_id = self.kwargs.get("organization_id")
        qs = Group.objects.filter(organization_id=org_id).select_related("parent")
        # Report 9 #23: a Group Admin sees his group and its sub-groups.
        group_ids = managed_group_ids(self.request.user)
        if group_ids is not None:
            qs = qs.filter(id__in=group_ids)
        return qs

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # A Group Admin not tagged to a group has no group to work inside, so
        # he does not create, rename or delete the organization's groups.
        if (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and role_name(request.user) == "group_admin"
            and managed_group_ids(request.user) is None
        ):
            raise PermissionDenied("Group Admins cannot change the organization's groups.")

    def _is_group_admin(self):
        return role_name(self.request.user) == "group_admin"

    def _validate_parent(self, parent, instance=None):
        """The parent must be a group of this organization, must not create a
        cycle, and — for a Group Admin (Report 9 #23) — must be his own group
        or one of its sub-groups (so he only ever builds sub-groups)."""
        org_id = int(self.kwargs.get("organization_id"))
        if parent is None:
            if self._is_group_admin():
                raise PermissionDenied("You can add sub-groups only within your own group.")
            return
        if parent.organization_id != org_id:
            raise ValidationError({"parent": "The parent group belongs to another organization."})
        if instance is not None and (
            parent.id == instance.id or parent.id in descendant_group_ids([instance.id])
        ):
            raise ValidationError({"parent": "A group cannot be placed under itself."})
        group_ids = managed_group_ids(self.request.user)
        if group_ids is not None and parent.id not in group_ids:
            raise PermissionDenied("You can add sub-groups only within your own group.")

    def _check_can_change(self, group):
        """Report 9 #23: a Group Admin edits/deletes only the sub-groups below
        his own group — never his own group or any other group."""
        if self._is_group_admin() and group.id not in group_admin_editable_group_ids(
            self.request.user
        ):
            raise PermissionDenied("You can change only the sub-groups within your own group.")

    def perform_create(self, serializer):
        org_id = self.kwargs.get("organization_id")
        org = get_object_or_404(Organization, id=org_id)
        self._validate_parent(serializer.validated_data.get("parent"))
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
                "data": self.get_serializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        self._check_can_change(instance)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        if "parent" in serializer.validated_data:
            self._validate_parent(serializer.validated_data["parent"], instance=instance)
        group = serializer.save()
        return Response(
            {
                "message": "Group updated.",
                "data": self.get_serializer(group).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self._check_can_change(instance)
        instance.delete()
        return Response(
            {"message": "Group deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )


class OrganizationMemberViewSet(ManagedOrgMixin, ModelViewSet):
    """CRUD for organization members.

    GET    /api/organizations/<org_id>/members/
    POST   /api/organizations/<org_id>/members/         (add member by email)
    DELETE /api/organizations/<org_id>/members/<id>/
    PATCH  /api/organizations/<org_id>/members/<id>/    (update group/is_admin)
    """

    serializer_class = OrganizationMemberSerializer
    permission_classes = [IsAuthenticated, HasOrgContentPermission]

    def get_queryset(self):
        org_id = self.kwargs.get("organization_id")
        qs = OrganizationMember.objects.filter(organization_id=org_id).select_related(
            "user__role", "group"
        )
        group_ids = managed_group_ids(self.request.user)
        if group_ids is not None:
            qs = qs.filter(group_id__in=group_ids)
        return qs

    def perform_create(self, serializer):
        org_id = self.kwargs.get("organization_id")
        org = get_object_or_404(Organization, id=org_id)
        extra = {}
        group_ids = managed_group_ids(self.request.user)
        if group_ids is not None:
            # A Group Admin's new members always join his own group.
            requested = serializer.validated_data.get("group_id")
            extra["group_id"] = requested if requested in group_ids else group_ids[0]
        serializer.save(organization=org, **extra)

    def _check_existing_user(self, email):
        """Report 9: an organization manager may add an EXISTING account only
        if it is a plain individual who belongs to no other organization —
        otherwise he could pull anyone (even staff) into his organization."""
        if managed_org_ids(self.request.user) is None or not email:
            return
        from apps.accounts.models import User

        existing = User.objects.filter(email__iexact=email).first()
        if existing is None:
            return
        if (
            role_name(existing) != "individual"
            or OrganizationMember.objects.filter(user=existing)
            .exclude(organization_id=self.kwargs.get("organization_id"))
            .exists()
        ):
            raise PermissionDenied(
                "This email belongs to an account you cannot add. Please contact CJ Admin."
            )

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
        self._check_existing_user(serializer.validated_data.get("user_email"))
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
        data = request.data
        org_id = int(self.kwargs.get("organization_id"))
        requester_is_ga = role_name(request.user) == "group_admin"
        if "group_id" in data:
            group_id = data.get("group_id") or None
            if (
                group_id is not None
                and not Group.objects.filter(id=group_id, organization_id=org_id).exists()
            ):
                raise ValidationError({"group_id": "Choose a group of this organization."})
            # A Group Admin moves members only within his group and sub-groups.
            group_ids = managed_group_ids(request.user)
            if group_ids is not None and (group_id is None or int(group_id) not in group_ids):
                raise PermissionDenied(
                    "You can place members only in your own group or sub-groups."
                )
            instance.group_id = int(group_id) if group_id is not None else None
        if data.get("is_admin") is not None:
            if requester_is_ga:
                raise PermissionDenied("Only the organization's admin can change admin rights.")
            instance.is_admin = _as_bool(data.get("is_admin"))
        if "is_group_admin" in data:
            self._require_group_admin_setup(request)
            self._set_group_admin(instance, _as_bool(data.get("is_group_admin")))
        if "can_view_member_reports" in data:
            # Report 9 #4/#13/#38: the Corp Admin sets (and later edits) a Group
            # Admin's "Can view & download members' reports" permission.
            self._require_group_admin_setup(request)
            allow = _as_bool(data.get("can_view_member_reports"))
            if allow and role_name(instance.user) != "group_admin":
                raise ValidationError(
                    {"can_view_member_reports": "This permission applies to Group Admins only."}
                )
            instance.can_view_member_reports = allow
        instance.save()
        return Response(
            {
                "message": "Member updated.",
                "data": OrganizationMemberSerializer(instance).data,
            },
            status=status.HTTP_200_OK,
        )

    @staticmethod
    def _require_group_admin_setup(request):
        if not can_set_up_group_admins(request.user):
            raise PermissionDenied(
                "Only the organization's admin can set up Group Admins and their rights."
            )

    @staticmethod
    def _set_group_admin(member, make):
        """Report 9 #37: tag an existing corporate individual as Group Admin of
        his group (or turn a Group Admin back into a corporate individual)."""
        from apps.accounts.models import Role

        current = role_name(member.user)
        if current not in ("individual", "group_admin"):
            raise ValidationError(
                {"is_group_admin": "Only a corporate individual can be made a Group Admin."}
            )
        if make:
            if member.group_id is None:
                raise ValidationError(
                    {"is_group_admin": "Choose the member's group before making him Group Admin."}
                )
            new_role, member.is_admin = "group_admin", True
        else:
            new_role, member.is_admin = "individual", False
            member.can_view_member_reports = False
        if current != new_role:
            member.user.role = Role.objects.get(name=new_role)
            member.user.save(update_fields=["role", "updated_at"])

    def create_group_admin(self, request, *args, **kwargs):
        """POST /api/organizations/<org_id>/group-admins/

        Report 9 #21 (SRS p.18 "Group Admins by corporate Admin"; Doc 9 §2.3):
        the Corp Admin / Corp Exclusive Admin (or CJ Admin) defines a Group
        Admin — Name, official Email, Employee ID, Group and Permissions. The
        user is created with the Group Admin role, linked as an admin member of
        this organization and that group, and sent the verification email.
        """
        from django.db import transaction

        from apps.accounts.models import Role, User
        from apps.accounts.serializers import UserWriteSerializer

        self._require_group_admin_setup(request)
        org = get_object_or_404(Organization, id=self.kwargs.get("organization_id"))
        if org.type not in CORPORATE_ORG_TYPES:
            raise ValidationError(
                {"organization": "Group Admins are set up for corporate organizations only."}
            )
        payload = GroupAdminCreateSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        d = payload.validated_data
        group = Group.objects.filter(id=d["group_id"], organization=org).first()
        if group is None:
            raise ValidationError({"group_id": "Choose a group of this organization."})
        if User.objects.filter(email__iexact=d["email"]).exists():
            raise ValidationError(
                {
                    "email": (
                        "A user with this email already exists. To make an existing member "
                        "a Group Admin, use 'Make Group Admin' on the member's row."
                    )
                }
            )
        role = Role.objects.get(name="group_admin")
        with transaction.atomic():
            user_serializer = UserWriteSerializer(
                data={"email": d["email"], "full_name": d["full_name"], "role": role.pk},
                context={"request": request},
            )
            user_serializer.is_valid(raise_exception=True)
            user = user_serializer.save()
            member = OrganizationMember.objects.create(
                organization=org,
                user=user,
                group=group,
                employee_id=d.get("employee_id", ""),
                is_admin=True,
                can_view_member_reports=d.get("can_view_member_reports", False),
            )
        data = OrganizationMemberSerializer(member).data
        data["invite_email_sent"] = getattr(user_serializer, "invite_email_sent", None)
        message = "Group Admin created and the verification email sent."
        if data["invite_email_sent"] is False:
            message = "Group Admin created, but the verification email could not be sent."
        return Response({"message": message, "data": data}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Member removed.", "data": {}},
            status=status.HTTP_200_OK,
        )


class OrganizationAssignmentViewSet(ManagedOrgMixin, ModelViewSet):
    """Assign published content to an organization (CJ_UC030, Doc 4).

    GET    /api/organizations/<org_id>/assignments/
    POST   /api/organizations/<org_id>/assignments/     (assign assessment/training/counseling)
    DELETE /api/organizations/<org_id>/assignments/<id>/

    Only org managers (organizations.add/change) may assign; the org's corporate
    individuals then see only the assessments assigned here (see
    ``apps.organizations.scoping``).
    """

    serializer_class = OrganizationAssignmentSerializer
    permission_classes = [IsAuthenticated, HasOrgContentPermission]

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
        # Report 9 #8: assigning (licensing) content to an organization is CJ
        # Admin's right; corporate admins then work with what was assigned.
        _require_cj_admin(request, "Only CJ Admin can assign content to an organization.")
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
        _require_cj_admin(request, "Only CJ Admin can remove content from an organization.")
        instance = self.get_object()
        instance.delete()
        return Response(
            {"message": "Assignment removed.", "data": {}},
            status=status.HTTP_200_OK,
        )


class AssessmentScheduleViewSet(ManagedOrgMixin, ModelViewSet):
    """CJ_UC053 — schedule an assessment for a corporate's employees + notify.

    GET    /api/organizations/<org_id>/schedules/
    POST   /api/organizations/<org_id>/schedules/
    DELETE /api/organizations/<org_id>/schedules/<id>/
    """

    serializer_class = AssessmentScheduleSerializer
    permission_classes = [IsAuthenticated, HasOrgContentPermission]

    def get_queryset(self):
        org_id = self.kwargs.get("organization_id")
        qs = AssessmentSchedule.objects.filter(organization_id=org_id).select_related(
            "assessment", "group"
        )
        group_ids = managed_group_ids(self.request.user)
        if group_ids is not None:
            qs = qs.filter(group_id__in=group_ids)
        return qs

    def _validate_target(self, assessment, group):
        """Report 9 #8/#26: a manager schedules only assessments CJ Admin
        assigned to his organization, and a Group Admin only for his group."""
        org_id = int(self.kwargs.get("organization_id"))
        if managed_org_ids(self.request.user) is not None and assessment is not None:
            assigned = OrganizationAssignment.objects.filter(
                organization_id=org_id, item_type="assessment", item_id=assessment.id
            ).exists()
            if not assigned:
                raise PermissionDenied(
                    "This assessment has not been assigned to your organization by CJ Admin."
                )
        if group is not None and group.organization_id != org_id:
            raise PermissionDenied("That group belongs to another organization.")
        group_ids = managed_group_ids(self.request.user)
        if group_ids is not None and (group is None or group.id not in group_ids):
            raise PermissionDenied("You can schedule assessments only for your own group.")

    def perform_create(self, serializer):
        org_id = self.kwargs.get("organization_id")
        org = get_object_or_404(Organization, id=org_id)
        self._validate_target(
            serializer.validated_data.get("assessment"), serializer.validated_data.get("group")
        )
        schedule = serializer.save(organization=org, created_by=self.request.user)
        self._notify_members(schedule)

    def partial_update(self, request, *args, **kwargs):
        """Report 9 #11: reschedule — change the date/time (and optionally the
        group) of an existing schedule; the members are notified again."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self._validate_target(
            serializer.validated_data.get("assessment", instance.assessment),
            serializer.validated_data.get("group", instance.group),
        )
        schedule = serializer.save()
        self._notify_members(schedule, rescheduled=True)
        return Response(
            {
                "message": "Assessment rescheduled and members notified.",
                "data": AssessmentScheduleSerializer(schedule).data,
            },
            status=status.HTTP_200_OK,
        )

    def _notify_members(self, schedule, rescheduled=False):
        from apps.notifications.models import notify_user

        members = OrganizationMember.objects.filter(
            organization=schedule.organization
        ).select_related("user")
        if schedule.group_id:
            # Report 9 #23: a group's sub-group members belong to it too.
            members = members.filter(
                group_id__in=[schedule.group_id, *descendant_group_ids([schedule.group_id])]
            )
        title = "Assessment rescheduled" if rescheduled else "Assessment scheduled"
        when = timezone.localtime(schedule.scheduled_at).strftime("%d %b %Y, %H:%M")
        verb = "has been rescheduled to" if rescheduled else "is scheduled for"
        body = f"'{schedule.assessment.title}' {verb} {when}."
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


class CorporateWebsiteViewSet(ManagedOrgMixin, ModelViewSet):
    """CJ_UC054/UC055 — a corporate's branded portal (single, per organization).

    GET    /api/organizations/<org_id>/website/       (retrieve, 404 if none)
    POST   /api/organizations/<org_id>/website/       (create + generate admin)
    PATCH  /api/organizations/<org_id>/website/       (customize: name/layout/logo/color)

    Report 9 #49: the logo may be uploaded (multipart field ``logo``) or, for
    older records, given as a ``logo_url``; whichever is saved last is used.
    """

    serializer_class = CorporateWebsiteSerializer
    permission_classes = [IsAuthenticated, HasOrgContentPermission]

    def _org(self):
        return get_object_or_404(Organization, id=self.kwargs.get("organization_id"))

    def retrieve(self, request, *args, **kwargs):
        org = self._org()
        website = getattr(org, "corporate_website", None)
        if website is None:
            return Response({"message": "OK", "data": None}, status=status.HTTP_200_OK)
        return Response(
            {"message": "OK", "data": self.get_serializer(website).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        # CJ_UC055: CJ Admin sets up the website and its admin login; the
        # organization's own admin then customizes it (Report 9 #49/#95).
        _require_cj_admin(request, "Only CJ Admin can set up an organization's website.")
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
            logo=serializer.validated_data.get("logo"),
            layout=serializer.validated_data.get("layout", "classic"),
            primary_color=serializer.validated_data.get("primary_color", "#4f46e5"),
            admin_user=admin_user,
        )
        data = self.get_serializer(website).data
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
        if role_name(request.user) == "group_admin":
            raise PermissionDenied("Only the organization's admin can customize its website.")
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
        # Report 9 #49: validate the edit (company name is editable, the logo
        # can be an upload) instead of copying raw request values.
        serializer = self.get_serializer(website, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("logo"):
            # A new upload replaces any earlier upload or typed URL.
            if website.logo:
                website.logo.delete(save=False)
            data["logo_url"] = ""
        elif "logo_url" in data or ("logo" in data and data["logo"] is None):
            # A typed URL (or an explicit removal) drops the uploaded file.
            if website.logo:
                website.logo.delete(save=False)
            data["logo"] = None
        website = serializer.save()
        return Response(
            {"message": "Website updated.", "data": self.get_serializer(website).data},
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
        # Report 9 #95: an exclusive organization's admin gets the Corporate
        # Exclusive role, not Corporate Admin.
        role_code = "corp_exclusive" if org.type == "corp_exclusive" else "corp_admin"
        role = Role.objects.filter(name=role_code).first()
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


def _public_site_data(website):
    """Non-sensitive branding shown on a corporate's portal (CJ_UC054)."""
    return {
        "organization_id": website.organization_id,
        "slug": website.slug,
        "company_name": website.company_name,
        # Report 9 #49: the uploaded logo (served via the API) or a typed URL.
        "logo_url": website.logo_src,
        "layout": website.layout,
        "primary_color": website.primary_color,
    }


class CorporateSitePublicView(APIView):
    """Public tenant branding by slug (CJ_UC054) — for rendering a corporate's
    branded portal at /site/<slug> (Report 9 #48/#95). No auth: only
    non-sensitive branding is exposed.

    GET /api/organizations/site/<slug>/
    """

    permission_classes = [AllowAny]
    # Public page: a stale token in the visitor's browser must not turn this
    # into a 401.
    authentication_classes = []

    def get(self, request, slug):
        website = CorporateWebsite.objects.filter(slug=slug, is_active=True).first()
        if website is None:
            return Response(
                {"error": {"code": "not_found", "message": "Site not found.", "details": {}}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"message": "OK", "data": _public_site_data(website)},
            status=status.HTTP_200_OK,
        )


class CorporateSiteLogoView(APIView):
    """Report 9 #49: the uploaded logo, streamed through the API so it loads
    wherever /api/* reaches the backend (media files are not proxied).

    GET /api/organizations/site/<slug>/logo/
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, slug):
        website = CorporateWebsite.objects.filter(slug=slug).first()
        if website is None or not website.logo:
            raise NotFound("Logo not found.")
        try:
            handle = website.logo.open("rb")
        except OSError as exc:
            raise NotFound("Logo not found.") from exc
        content_type = mimetypes.guess_type(website.logo.name)[0] or "application/octet-stream"
        response = FileResponse(handle, content_type=content_type)
        response["Cache-Control"] = "public, max-age=300"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class MyCorporateSiteView(APIView):
    """Report 9 #51/#52: the branding of the signed-in member's organization
    portal (if it has an active website), so the app's top bar can carry the
    company logo/name after a portal sign-in. ``data`` is null otherwise.

    GET /api/organizations/my-site/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        website = (
            CorporateWebsite.objects.filter(
                is_active=True, organization__members__user=request.user
            )
            .order_by("id")
            .first()
        )
        return Response(
            {"message": "OK", "data": _public_site_data(website) if website else None},
            status=status.HTTP_200_OK,
        )

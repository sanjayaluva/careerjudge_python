"""Serializers for the organizations module."""

import os
import re

from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer

from .models import (
    AssessmentSchedule,
    CorporateWebsite,
    Group,
    Organization,
    OrganizationAssignment,
    OrganizationMember,
)


class GroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source="members.count", read_only=True)
    # Report 9 #23: groups nest; ``parent`` is validated against the
    # organization and the requester's scope in GroupViewSet.
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False, allow_null=True
    )
    parent_name = serializers.CharField(source="parent.name", read_only=True, default=None)
    # Whether the requester may edit/delete this group (a Group Admin: only
    # the sub-groups below his own group).
    can_manage = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            "id",
            "organization",
            "name",
            "parent",
            "parent_name",
            "region_division",
            "description",
            "member_count",
            "can_manage",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]

    def get_can_manage(self, obj) -> bool:
        from .scoping import group_admin_editable_group_ids, role_name

        request = self.context.get("request")
        if request is None or role_name(request.user) != "group_admin":
            return True
        if "_ga_editable" not in self.context:
            self.context["_ga_editable"] = set(group_admin_editable_group_ids(request.user))
        return obj.id in self.context["_ga_editable"]


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_email = serializers.EmailField(write_only=True, required=True)
    group_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    # Doc 9 §2.3: when a corporate admin onboards a NEW corporate individual,
    # they supply the person's name (and optionally Employee ID); the user is
    # created and a signup email is sent. When ``full_name`` is omitted the
    # endpoint keeps its original behaviour of adding an EXISTING user by email.
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)
    # Report 9 #21/#37: explicit Group Admin indicator on the member row.
    is_group_admin = serializers.SerializerMethodField()

    class Meta:
        model = OrganizationMember
        fields = [
            "id",
            "organization",
            "user",
            "user_email",
            "full_name",
            "group",
            "group_id",
            "group_name",
            "employee_id",
            "is_admin",
            "is_group_admin",
            "can_view_member_reports",
            "joined_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "user",
            "group",
            "is_group_admin",
            # Report 9 #4: set only by the Corp Admin through the member update.
            "can_view_member_reports",
            "joined_at",
        ]

    def get_is_group_admin(self, obj) -> bool:
        role = getattr(obj.user, "role", None)
        return bool(role and role.name == "group_admin")

    def create(self, validated_data):
        user_email = validated_data.pop("user_email")
        group_id = validated_data.pop("group_id", None)
        full_name = (validated_data.pop("full_name", "") or "").strip()
        organization = validated_data["organization"]

        user = User.objects.filter(email__iexact=user_email).first()
        if user is None:
            if not full_name:
                raise serializers.ValidationError({"user_email": "User not found with this email."})
            # Corporate admin onboarding a new corporate individual (Doc 9 §2.3):
            # create the account (inactive until they verify) and email a link.
            user = _create_corporate_individual(user_email, full_name)

        if OrganizationMember.objects.filter(organization=organization, user=user).exists():
            raise serializers.ValidationError(
                {"user_email": "User is already a member of this organization."}
            )

        member = OrganizationMember.objects.create(
            organization=organization,
            user=user,
            group_id=group_id,
            employee_id=validated_data.get("employee_id", ""),
            is_admin=validated_data.get("is_admin", False),
        )
        return member


class GroupAdminCreateSerializer(serializers.Serializer):
    """Report 9 #21 (SRS p.18): the Corp Admin's "Add Group Admin" form —
    Name, official Email, Employee ID, Group and Permissions."""

    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    employee_id = serializers.CharField(max_length=50, required=False, allow_blank=True)
    group_id = serializers.IntegerField()
    can_view_member_reports = serializers.BooleanField(required=False, default=False)


def _create_corporate_individual(email: str, full_name: str):
    """Create an inactive ``individual`` user and email them a signup link."""
    from django.utils.crypto import get_random_string

    from apps.accounts.models import Role, UserProfile
    from apps.accounts.services import create_email_verification_token, send_verification_email

    role = Role.objects.filter(name="individual").first()
    user = User.objects.create_user(
        email=email.strip().lower(),
        password=get_random_string(length=12),
        full_name=full_name,
        is_active=False,
        is_email_verified=False,
        role=role,
    )
    UserProfile.objects.get_or_create(user=user)
    try:
        token = create_email_verification_token(user)
        send_verification_email(user, token)
    except Exception:
        # Email failure must not block onboarding.
        pass
    return user


class OrganizationAssignmentSerializer(serializers.ModelSerializer):
    """CJ Admin assigns a published assessment / training / counseling item to
    an organization, so only the org's users see it (CJ_UC030, Doc 4)."""

    assigned_by_name = serializers.CharField(
        source="assigned_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = OrganizationAssignment
        fields = [
            "id",
            "organization",
            "item_type",
            "item_id",
            "assigned_by",
            "assigned_by_name",
            "assigned_at",
        ]
        read_only_fields = ["id", "organization", "assigned_by", "assigned_by_name", "assigned_at"]


class AssessmentScheduleSerializer(serializers.ModelSerializer):
    """CJ_UC053: a corporate/group admin schedules an assessment for employees."""

    assessment_title = serializers.CharField(source="assessment.title", read_only=True)
    group_name = serializers.CharField(source="group.name", read_only=True, default=None)

    class Meta:
        model = AssessmentSchedule
        fields = [
            "id",
            "organization",
            "group",
            "assessment",
            "assessment_title",
            "group_name",
            "scheduled_at",
            "created_by",
            "notified",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "assessment_title",
            "group_name",
            "created_by",
            "notified",
            "created_at",
        ]


# Report 9 #49: uploaded corporate logos — raster images only (no SVG, which
# can carry script), at most 2 MB.
LOGO_MAX_BYTES = 2 * 1024 * 1024
LOGO_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")


class CorporateWebsiteSerializer(serializers.ModelSerializer):
    """CJ_UC054/UC055: a corporate's branded portal."""

    admin_email = serializers.EmailField(source="admin_user.email", read_only=True, default=None)
    # Write-only upload; reads use ``logo_src`` (uploaded file or typed URL).
    logo = serializers.ImageField(write_only=True, required=False, allow_null=True)
    logo_src = serializers.CharField(read_only=True)

    class Meta:
        model = CorporateWebsite
        fields = [
            "id",
            "organization",
            "slug",
            "company_name",
            "logo_url",
            "logo",
            "logo_src",
            "layout",
            "primary_color",
            "admin_user",
            "admin_email",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "slug",
            "admin_user",
            "admin_email",
            "created_at",
            "updated_at",
        ]

    def validate_company_name(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Company name is required.")
        return value

    def validate_primary_color(self, value):
        if not HEX_COLOR_RE.match(value or ""):
            raise serializers.ValidationError("Enter a colour as a hex code, e.g. #4f46e5.")
        return value

    def validate_logo(self, value):
        if value is None:
            return value
        ext = os.path.splitext(value.name or "")[1].lower()
        if ext not in LOGO_EXTENSIONS:
            raise serializers.ValidationError("Upload a PNG, JPG, GIF or WebP image.")
        if value.size > LOGO_MAX_BYTES:
            raise serializers.ValidationError("The logo must be 2 MB or smaller.")
        return value


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source="members.count", read_only=True)
    group_count = serializers.IntegerField(source="groups.count", read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "type",
            "status",
            "description",
            "manager_name",
            "tax_id",
            "contact_email",
            "contact_phone",
            "website",
            "address_line1",
            "address_line2",
            "city",
            "state",
            "country",
            "postal_code",
            "member_count",
            "group_count",
            "groups",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_groups(self, obj):
        # Report 9 #23: a Group Admin sees only his group and its sub-groups.
        from .scoping import managed_group_ids

        groups = obj.groups.select_related("parent").all()
        request = self.context.get("request")
        if request is not None:
            group_ids = managed_group_ids(request.user)
            if group_ids is not None:
                groups = groups.filter(id__in=group_ids)
        return GroupSerializer(groups, many=True, context=self.context).data


class OrganizationListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views (no nested groups)."""

    member_count = serializers.IntegerField(source="members.count", read_only=True)
    group_count = serializers.IntegerField(source="groups.count", read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "type",
            "status",
            "contact_email",
            "member_count",
            "group_count",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

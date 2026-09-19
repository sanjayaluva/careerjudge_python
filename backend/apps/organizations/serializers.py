"""Serializers for the organizations module."""

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

    class Meta:
        model = Group
        fields = [
            "id",
            "organization",
            "name",
            "region_division",
            "description",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "organization", "created_at", "updated_at"]


class OrganizationMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_email = serializers.EmailField(write_only=True, required=True)
    group_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    # Doc 9 §2.3: when a corporate admin onboards a NEW corporate individual,
    # they supply the person's name (and optionally Employee ID); the user is
    # created and a signup email is sent. When ``full_name`` is omitted the
    # endpoint keeps its original behaviour of adding an EXISTING user by email.
    full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

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
            "employee_id",
            "is_admin",
            "joined_at",
        ]
        read_only_fields = ["id", "organization", "user", "group", "joined_at"]

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


class CorporateWebsiteSerializer(serializers.ModelSerializer):
    """CJ_UC054/UC055: a corporate's branded portal."""

    admin_email = serializers.EmailField(source="admin_user.email", read_only=True, default=None)

    class Meta:
        model = CorporateWebsite
        fields = [
            "id",
            "organization",
            "slug",
            "company_name",
            "logo_url",
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


class OrganizationSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source="members.count", read_only=True)
    group_count = serializers.IntegerField(source="groups.count", read_only=True)
    groups = GroupSerializer(many=True, read_only=True)

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

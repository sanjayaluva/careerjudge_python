"""Serializers for the organizations module."""

from rest_framework import serializers

from apps.accounts.models import User
from apps.accounts.serializers import UserSerializer

from .models import Group, Organization, OrganizationMember


class GroupSerializer(serializers.ModelSerializer):
    member_count = serializers.IntegerField(source="members.count", read_only=True)

    class Meta:
        model = Group
        fields = [
            "id",
            "organization",
            "name",
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

    class Meta:
        model = OrganizationMember
        fields = [
            "id",
            "organization",
            "user",
            "user_email",
            "group",
            "group_id",
            "is_admin",
            "joined_at",
        ]
        read_only_fields = ["id", "organization", "user", "group", "joined_at"]

    def create(self, validated_data):
        user_email = validated_data.pop("user_email")
        group_id = validated_data.pop("group_id", None)
        organization = validated_data["organization"]

        try:
            user = User.objects.get(email__iexact=user_email)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"user_email": "User not found with this email."}
            ) from exc

        if OrganizationMember.objects.filter(organization=organization, user=user).exists():
            raise serializers.ValidationError(
                {"user_email": "User is already a member of this organization."}
            )

        member = OrganizationMember.objects.create(
            organization=organization,
            user=user,
            group_id=group_id,
            is_admin=validated_data.get("is_admin", False),
        )
        return member


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

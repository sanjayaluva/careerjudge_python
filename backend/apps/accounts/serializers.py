"""Serializers for the accounts module."""

from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import (
    EmailVerificationToken,
    ModuleRight,
    PasswordResetToken,
    Role,
    User,  # User is the concrete model from get_user_model()
    UserProfile,
)

# ---------------------------------------------------------------------------
# Auth serializers
# ---------------------------------------------------------------------------


class SignupSerializer(serializers.Serializer):
    """POST /api/auth/signup — UC001."""

    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True, validators=[validate_password])
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists. Please log in."
            )
        return value.lower()

    @transaction.atomic
    def create(self, validated_data: dict) -> User:
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data.get("full_name", ""),
            is_active=False,  # requires email verification per UC001
            is_email_verified=False,
        )
        # assign default 'individual' role if it exists
        try:
            individual_role = Role.objects.get(name="individual")
            user.role = individual_role
            user.save(update_fields=["role"])
        except Role.DoesNotExist:
            pass
        # create empty profile
        UserProfile.objects.get_or_create(user=user)
        return user


class LoginSerializer(serializers.Serializer):
    """POST /api/auth/login — UC007."""

    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        email = attrs.get("email", "").lower()
        password = attrs.get("password", "")
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid credentials.") from exc
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account not activated. Please verify your email.")
        attrs["user"] = user
        return attrs


class EmailVerificationSerializer(serializers.Serializer):
    """POST /api/auth/verify-email."""

    token = serializers.UUIDField()

    def validate(self, attrs: dict) -> dict:
        try:
            token = EmailVerificationToken.objects.select_related("user").get(token=attrs["token"])
        except EmailVerificationToken.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid verification token.") from exc
        if not token.is_valid:
            raise serializers.ValidationError(
                "Token expired or already used. Please request a new one."
            )
        attrs["token"] = token
        return attrs


class ResendVerificationSerializer(serializers.Serializer):
    """POST /api/auth/resend-verification."""

    email = serializers.EmailField(max_length=255)

    def validate_email(self, value: str) -> str:
        # Always return lowercased email — never leak whether email exists.
        # The view handles both "user exists" and "user does not exist"
        # by returning the same success response.
        return value.lower()


class ForgotPasswordSerializer(serializers.Serializer):
    """POST /api/auth/forgot-password."""

    email = serializers.EmailField(max_length=255)

    def validate_email(self, value: str) -> str:
        # Always return success — never leak whether email exists
        return value.lower()


class ResetPasswordSerializer(serializers.Serializer):
    """POST /api/auth/reset-password."""

    token = serializers.UUIDField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate(self, attrs: dict) -> dict:
        try:
            token = PasswordResetToken.objects.select_related("user").get(token=attrs["token"])
        except PasswordResetToken.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid reset token.") from exc
        if not token.is_valid:
            raise serializers.ValidationError(
                "Token expired or already used. Please request a new one."
            )
        attrs["token"] = token
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """POST /api/me/change-password."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


# ---------------------------------------------------------------------------
# Profile serializers
# ---------------------------------------------------------------------------


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = [
            # Common
            "gender",
            "date_of_birth",
            "mobile",
            "avatar",
            "bio",
            # Name fields
            "first_name",
            "middle_name",
            "last_name",
            # Location
            "country_of_origin",
            "state_province",
            "city",
            "postal_code",
            "address_line1",
            "address_line2",
            # Individual user fields
            "occupation",
            "current_position",
            "highest_education",
            "work_experience",
            "education_level",
            "institution_name",
            "place_of_institution",
            "location",
            "assessment_package_allocated",
            # Professional fields
            "domain_experience",
            "pan_number",
            "bank_account_number",
            "bank_name",
            "branch_name",
            "ifsc_code",
            "contact_address",
            "permanent_address",
            # Channel Partner fields
            "channel_partner_agreement_id",
            "contract_period",
        ]
        read_only_fields = ["avatar"]  # avatar handled via separate upload endpoint


class UserSerializer(serializers.ModelSerializer):
    """Read serializer for current user and admin user views."""

    profile = UserProfileSerializer(read_only=True)
    role = serializers.SlugRelatedField(slug_field="name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "phone",
            "is_active",
            "is_email_verified",
            "is_trial_user",
            "is_superuser",
            "is_staff",
            "role",
            "profile",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_active",
            "is_email_verified",
            "is_superuser",
            "is_staff",
            "role",
            "profile",
            "created_at",
            "updated_at",
        ]


class UserWriteSerializer(serializers.ModelSerializer):
    """Write serializer for admin user management.

    Used for both create and update. Email uniqueness is enforced but
    excludes the current instance during PATCH (so editing a user without
    changing their email doesn't trigger a false uniqueness error).
    """

    class Meta:
        model = User
        fields = [
            "email",
            "full_name",
            "phone",
            "is_active",
            "is_email_verified",
            "is_trial_user",
            "role",
            "password",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": False, "allow_blank": True},
            "email": {"required": False},  # allow PATCH without email
            "full_name": {"required": False},
        }

    def validate_email(self, value: str) -> str:
        """Email must be unique, but exclude the current instance on update."""
        if not value:
            return value
        value = value.lower()
        qs = User.objects.filter(email__iexact=value)
        # If updating, exclude the current user
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return value

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password", None)
        # Use create_user to properly hash the password and normalize email
        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save(update_fields=["password"])
        else:
            # generate random password and email it (per UC002)
            from django.utils.crypto import get_random_string

            random_pw = get_random_string(length=12)
            user.set_password(random_pw)
            user.save(update_fields=["password"])
        UserProfile.objects.get_or_create(user=user)
        return user

    def update(self, instance: User, validated_data: dict) -> User:
        """Update user. Hash password if provided; ignore blank password."""
        password = validated_data.pop("password", None)
        if password:  # only update if a non-empty password was sent
            instance.set_password(password)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class UpdateProfileSerializer(serializers.ModelSerializer):
    """PATCH /api/me/ — update current user's basic info + profile.

    The profile field is a dict of profile attributes (not a nested
    serializer) to avoid strict validation on gender choices etc.
    """

    profile = serializers.DictField(
        required=False, child=serializers.CharField(allow_blank=True, allow_null=True)
    )

    class Meta:
        model = User
        fields = ["full_name", "phone", "profile"]

    def update(self, instance: User, validated_data: dict) -> User:
        profile_data = validated_data.pop("profile", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if profile_data:
            profile, _ = UserProfile.objects.get_or_create(user=instance)
            # Only set fields that exist on the UserProfile model
            valid_fields = {f.name for f in UserProfile._meta.get_fields()}
            for attr, value in profile_data.items():
                if attr in valid_fields and attr != "id" and attr != "user":
                    # Convert empty strings to None for nullable fields
                    if value == "" and UserProfile._meta.get_field(attr).null:
                        value = None
                    setattr(profile, attr, value)
            profile.save()
        return instance


# ---------------------------------------------------------------------------
# Role / ModuleRight serializers
# ---------------------------------------------------------------------------


class ModuleRightSerializer(serializers.ModelSerializer):
    is_inherited = serializers.SerializerMethodField()

    class Meta:
        model = ModuleRight
        fields = ["id", "role", "module", "action", "is_inherited", "created_at"]
        read_only_fields = ["id", "is_inherited", "created_at"]

    def get_is_inherited(self, obj) -> bool:
        """True if this right is inherited from the role's base_role (cannot be removed)."""
        role = obj.role
        if not role.base_role_id:
            return False
        return (obj.module, obj.action) in role.inherited_right_keys


class RoleSerializer(serializers.ModelSerializer):
    rights = ModuleRightSerializer(many=True, read_only=True)
    effective_rights = ModuleRightSerializer(many=True, read_only=True)
    user_count = serializers.IntegerField(source="users.count", read_only=True)
    base_role_name = serializers.CharField(source="base_role.name", read_only=True, default=None)

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "is_system",
            "is_frozen",
            "base_role",
            "base_role_name",
            "rights",
            "effective_rights",
            "user_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_system", "is_frozen", "created_at", "updated_at"]


class CreateCustomRoleSerializer(serializers.ModelSerializer):
    """POST /api/accounts/roles/ — create a custom role.

    Fields:
      - name (required, unique): the custom role name (e.g. 'Senior Reviewer')
      - description (optional): free text
      - base_role (optional): ID of a system role whose permissions are inherited
        and cannot be removed from this custom role.
    """

    # Explicit CharField — prevents DRF from auto-detecting choices from the model
    # (Role.name used to have choices=ROLE_CHOICES; even though it's removed now,
    # being explicit avoids any ambiguity).
    name = serializers.CharField(max_length=100, required=True)
    description = serializers.CharField(required=False, allow_blank=True)
    base_role = serializers.PrimaryKeyRelatedField(
        queryset=Role.objects.filter(is_system=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Role
        fields = ["name", "description", "base_role"]

    def validate_name(self, value: str) -> str:
        """Custom role name must be unique and not clash with system role names."""
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name is required.")
        # Check it doesn't clash with a system role name
        system_names = [code for code, _ in Role.ROLE_CHOICES]
        if value.lower() in [n.lower() for n in system_names]:
            raise serializers.ValidationError(
                "Cannot use a system role name. Choose a different name."
            )
        if Role.objects.filter(name__iexact=value).exists():
            raise serializers.ValidationError("A role with this name already exists.")
        return value

    def validate_base_role(self, value) -> "Role | None":
        """base_role must be a system role if provided."""
        if value is None:
            return None
        if not value.is_system:
            raise serializers.ValidationError("base_role must be a system (built-in) role.")
        return value

    def create(self, validated_data: dict) -> Role:
        """Create a custom role and copy base_role's permissions (as inherited)."""
        base_role = validated_data.get("base_role")
        role = Role.objects.create(
            name=validated_data["name"],
            description=validated_data.get("description", ""),
            base_role=base_role,
            is_system=False,
            is_frozen=False,
        )
        # Copy base_role's permissions to the custom role (so effective_rights works
        # even without querying base_role). These are marked as inherited via the
        # is_inherited serializer field.
        if base_role:
            for right in base_role.rights.all():
                ModuleRight.objects.get_or_create(
                    role=role, module=right.module, action=right.action
                )
        return role


class AssignRoleSerializer(serializers.Serializer):
    """POST /api/accounts/users/<id>/assign-role/.

    Accepts role_id (preferred) or role_name (backward compat with system roles).
    """

    role_id = serializers.IntegerField(required=False)
    role_name = serializers.CharField(max_length=100, required=False)

    def validate(self, attrs: dict) -> dict:
        if not attrs.get("role_id") and not attrs.get("role_name"):
            raise serializers.ValidationError("Either role_id or role_name is required.")
        # Resolve to a Role instance
        role = None
        if attrs.get("role_id"):
            try:
                role = Role.objects.get(id=attrs["role_id"])
            except Role.DoesNotExist as exc:
                raise serializers.ValidationError({"role_id": "Role not found."}) from exc
        else:
            try:
                role = Role.objects.get(name=attrs["role_name"])
            except Role.DoesNotExist as exc:
                raise serializers.ValidationError({"role_name": "Role not found."}) from exc
        attrs["role"] = role
        return attrs


class AssignPermissionSerializer(serializers.Serializer):
    """POST /api/accounts/roles/<id>/assign-permission/ — add a custom permission."""

    module = serializers.ChoiceField(choices=[c[0] for c in ModuleRight.MODULE_CHOICES])
    action = serializers.ChoiceField(choices=[c[0] for c in ModuleRight.ACTION_CHOICES])


class RemovePermissionSerializer(serializers.Serializer):
    """POST /api/accounts/roles/<id>/remove-permission/ — remove a custom permission.

    Only allowed for custom roles, and only for permissions NOT inherited from
    the base_role.
    """

    module = serializers.ChoiceField(choices=[c[0] for c in ModuleRight.MODULE_CHOICES])
    action = serializers.ChoiceField(choices=[c[0] for c in ModuleRight.ACTION_CHOICES])

"""Views for /api/accounts/ endpoints (admin user/role management)."""

import csv
import io

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.permissions import HasModulePermission

from .models import ModuleRight, Role, User
from .serializers import (
    AssignPermissionSerializer,
    AssignRoleSerializer,
    CreateCustomRoleSerializer,
    ModuleRightSerializer,
    RemovePermissionSerializer,
    RoleSerializer,
    UserSerializer,
    UserWriteSerializer,
)
from .services import assign_permission_to_role


class HasAccountsPermission(HasModulePermission):
    module = "accounts"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
    }


class UserViewSet(ModelViewSet):
    """CRUD for users — admin only.

    GET    /api/accounts/users/
    POST   /api/accounts/users/
    GET    /api/accounts/users/<id>/
    PATCH  /api/accounts/users/<id>/
    DELETE /api/accounts/users/<id>/
    POST   /api/accounts/users/<id>/assign-role/
    """

    queryset = User.objects.select_related("role", "profile").all()
    permission_classes = [IsAuthenticated, HasAccountsPermission]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["email", "full_name", "phone"]
    ordering_fields = ["created_at", "email", "full_name"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Allow filtering by role name via ?role=sme query param."""
        qs = super().get_queryset()
        role_name = self.request.query_params.get("role")
        if role_name:
            qs = qs.filter(role__name=role_name)
        return qs

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return UserWriteSerializer
        return UserSerializer

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
        user = serializer.save()
        return Response(
            {
                "message": "User created.",
                "data": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "User updated.",
                "data": UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        # Individual user deletion rules (per client clarification):
        # - CJ Admin (superuser or has accounts.delete) → can delete ANY individual user
        # - Corp Admin / Corp Exclusive → can delete individual users WITHIN their org only
        # - Group Admin → can delete individual users within their org's groups
        # - Other roles → cannot delete individual users (403)
        if instance.role and instance.role.name == "individual":
            requester = request.user

            # CJ Admin or superuser → full access
            if requester.is_superuser:
                pass  # allowed
            elif requester.role and requester.role.name == "cj_admin":
                pass  # allowed — CJ Admin can delete any individual user
            elif requester.role and requester.role.name in (
                "corp_admin",
                "corp_exclusive",
                "group_admin",
                "channel_partner",
            ):
                # Org-scoped: can only delete individual users within their organization
                from apps.organizations.models import OrganizationMember

                requester_orgs = OrganizationMember.objects.filter(user=requester).values_list(
                    "organization_id", flat=True
                )
                target_orgs = OrganizationMember.objects.filter(user=instance).values_list(
                    "organization_id", flat=True
                )

                # Check if the target user shares at least one org with the requester
                if not set(requester_orgs).intersection(set(target_orgs)):
                    return Response(
                        {
                            "error": {
                                "code": "forbidden",
                                "message": "Cannot delete individual users from other organizations.",
                                "details": {},
                            }
                        },
                        status=status.HTTP_403_FORBIDDEN,
                    )
            else:
                return Response(
                    {
                        "error": {
                            "code": "forbidden",
                            "message": "You do not have permission to delete individual users.",
                            "details": {},
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

        instance.delete()
        return Response(
            {"message": "User deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )


class AssignRoleView(APIView):
    """POST /api/accounts/users/<id>/assign-role/."""

    permission_classes = [IsAuthenticated]

    def post(self, request, user_id):
        # Require accounts.change permission
        if not request.user.has_module_right("accounts", "change"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You do not have permission to assign roles.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        user = get_object_or_404(User, id=user_id)
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = serializer.validated_data["role"]
        user.role = role
        user.save(update_fields=["role", "updated_at"])
        return Response(
            {
                "message": f"Role '{role.name}' assigned.",
                "data": {"user_id": user.id, "role": role.name, "role_id": role.id},
            },
            status=status.HTTP_200_OK,
        )


class RoleViewSet(ModelViewSet):
    """CRUD for roles — admin only.

    GET    /api/accounts/roles/                       — list all roles (system + custom)
    POST   /api/accounts/roles/                       — create a custom role
    GET    /api/accounts/roles/<id>/                  — retrieve a role
    PATCH  /api/accounts/roles/<id>/                  — update description (custom only)
    DELETE /api/accounts/roles/<id>/                  — delete (custom only, no users)
    POST   /api/accounts/roles/<id>/assign-permission/  — add custom permission
    POST   /api/accounts/roles/<id>/remove-permission/  — remove custom permission
    """

    queryset = Role.objects.prefetch_related("rights", "users", "base_role").all()
    permission_classes = [IsAuthenticated, HasAccountsPermission]
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def get_serializer_class(self):
        if self.action == "create":
            return CreateCustomRoleSerializer
        return RoleSerializer

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
        role = serializer.save()
        return Response(
            {
                "message": "Custom role created.",
                "data": RoleSerializer(role).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        """Only custom roles can be updated, and only description + base_role."""
        kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "System roles cannot be modified.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        # Only allow description updates (name + base_role are immutable after creation)
        if "description" in request.data:
            instance.description = request.data["description"]
            instance.save(update_fields=["description", "updated_at"])
        return Response(
            {
                "message": "Role updated.",
                "data": RoleSerializer(instance).data,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_system:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "System roles cannot be deleted.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if instance.users.exists():
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Cannot delete a role that has users assigned. "
                        "Reassign users first.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return Response(
            {"message": "Custom role deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )


class AssignPermissionView(APIView):
    """POST /api/accounts/roles/<id>/assign-permission/ — add a custom permission.

    Only allowed for custom (non-system) roles.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, role_id):
        if not request.user.has_module_right("accounts", "change"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You do not have permission to assign permissions.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        role = get_object_or_404(Role, id=role_id)
        if role.is_system:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Cannot modify permissions on a system (frozen) role.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = AssignPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        right = assign_permission_to_role(
            role,
            serializer.validated_data["module"],
            serializer.validated_data["action"],
        )
        return Response(
            {
                "message": "Permission added to custom role.",
                "data": ModuleRightSerializer(right).data,
            },
            status=status.HTTP_201_CREATED,
        )


class RemovePermissionView(APIView):
    """POST /api/accounts/roles/<id>/remove-permission/ — remove a custom permission.

    Only allowed for custom (non-system) roles, and only for permissions NOT
    inherited from the base_role.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, role_id):
        if not request.user.has_module_right("accounts", "change"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You do not have permission to remove permissions.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        role = get_object_or_404(Role, id=role_id)
        if role.is_system:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Cannot remove permissions from a system (frozen) role.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = RemovePermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        module = serializer.validated_data["module"]
        action = serializer.validated_data["action"]

        # Check if this permission is inherited from base_role — cannot remove
        if (module, action) in role.inherited_right_keys:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Cannot remove inherited permission {module}.{action} "
                        f"(inherited from base role '{role.base_role.name}').",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        deleted, _ = ModuleRight.objects.filter(role=role, module=module, action=action).delete()
        if not deleted:
            return Response(
                {
                    "error": {
                        "code": "not_found",
                        "message": f"Permission {module}.{action} not found on this role.",
                        "details": {},
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"message": f"Permission {module}.{action} removed.", "data": {}},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Bulk user upload + CSV template download (SRS page 18, admin spec 2.3)
# ---------------------------------------------------------------------------


class BulkUserUploadView(APIView):
    """POST /api/accounts/users/bulk-upload/ — upload CSV of users.

    Per SRS page 18 + admin spec section 2.3:
    - Corporate Admin, Corporate Exclusive Admin, Group Admin can bulk upload
    - CSV format: full_name, email, (optional) phone, (optional) role_name
    - System creates users, sends signup emails, returns summary

    Actors with permission: anyone with accounts.add right
    (cj_admin, corp_admin, corp_exclusive)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.has_module_right("accounts", "add"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You do not have permission to add users.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        file = request.FILES.get("file")
        if not file:
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "No file uploaded. Please upload a CSV file.",
                        "details": {"file": ["This field is required."]},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not file.name.endswith(".csv"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "File must be a CSV (.csv extension).",
                        "details": {"file": ["Only CSV files are accepted."]},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Decode and parse CSV
        try:
            decoded = file.read().decode("utf-8-sig")  # handle BOM
        except UnicodeDecodeError:
            try:
                decoded = file.read().decode("latin-1")
            except Exception as exc:
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": f"Could not decode file: {exc}",
                            "details": {},
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        reader = csv.DictReader(io.StringIO(decoded))

        # Validate required columns
        required_cols = {"full_name", "email"}
        actual_cols = {col.strip().lower() for col in (reader.fieldnames or [])}
        if not required_cols.issubset(actual_cols):
            missing = required_cols - actual_cols
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": f"Missing required CSV columns: {', '.join(missing)}. "
                        f"Required: full_name, email. Optional: phone, role_name.",
                        "details": {"columns": list(missing)},
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get default role (individual)
        try:
            default_role = Role.objects.get(name="individual")
        except Role.DoesNotExist:
            default_role = None

        created = []
        skipped = []
        errors = []

        for row_num, row in enumerate(reader, start=2):  # start=2 (1=header)
            full_name = (row.get("full_name") or "").strip()
            email = (row.get("email") or "").strip().lower()
            phone = (row.get("phone") or "").strip()
            role_name = (row.get("role_name") or "").strip().lower()

            # Skip comment rows (lines starting with #)
            if full_name.startswith("#"):
                continue

            # Skip rows that don't look like valid data (no email AND no name)
            if not email and not full_name:
                continue

            if not email:
                errors.append({"row": row_num, "email": "", "error": "Email is empty"})
                continue

            if not full_name:
                errors.append({"row": row_num, "email": email, "error": "Full name is empty"})
                continue

            # Skip if email doesn't look like an email (must contain @)
            if "@" not in email:
                errors.append(
                    {
                        "row": row_num,
                        "email": email,
                        "error": "Invalid email format (missing @)",
                    }
                )
                continue

            # Check duplicate
            if User.objects.filter(email__iexact=email).exists():
                skipped.append({"row": row_num, "email": email, "reason": "Email already exists"})
                continue

            # Resolve role
            role = default_role
            if role_name:
                try:
                    role = Role.objects.get(name=role_name)
                except Role.DoesNotExist:
                    errors.append(
                        {
                            "row": row_num,
                            "email": email,
                            "error": f"Role '{role_name}' not found",
                        }
                    )
                    continue

            # Create user
            try:
                from django.utils.crypto import get_random_string

                random_pw = get_random_string(length=12)
                user = User.objects.create_user(
                    email=email,
                    password=random_pw,
                    full_name=full_name,
                    is_active=False,  # requires email verification
                    is_email_verified=False,
                    role=role,
                )
                if phone:
                    user.phone = phone
                    user.save(update_fields=["phone"])
                from apps.accounts.models import UserProfile

                UserProfile.objects.get_or_create(user=user)
                created.append({"row": row_num, "email": email, "full_name": full_name})
            except Exception as exc:
                errors.append({"row": row_num, "email": email, "error": str(exc)})

        return Response(
            {
                "message": f"Bulk upload complete: {len(created)} created, "
                f"{len(skipped)} skipped, {len(errors)} errors.",
                "data": {
                    "created_count": len(created),
                    "skipped_count": len(skipped),
                    "error_count": len(errors),
                    "created": created,
                    "skipped": skipped,
                    "errors": errors,
                },
            },
            status=status.HTTP_200_OK,
        )


class BulkUserTemplateView(APIView):
    """GET /api/accounts/users/bulk-upload/template/ — download CSV template.

    Returns a CSV file with the correct column headers + a sample row.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="careerjudge_bulk_users_template.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(["full_name", "email", "phone", "role_name"])
        writer.writerow(["John Doe", "john.doe@example.com", "+1234567890", "individual"])
        writer.writerow(["Jane Smith", "jane.smith@example.com", "", ""])

        return response

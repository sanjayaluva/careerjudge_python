"""Views for /api/accounts/ endpoints (admin user/role management)."""

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
        # Per UC004: CJ Admin cannot delete individual/corporate-individual users
        if instance.role and instance.role.name == "individual":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Cannot delete individual users.",
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

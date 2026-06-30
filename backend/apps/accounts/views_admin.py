"""Views for /api/accounts/ endpoints (admin user/role management)."""

from django.shortcuts import get_object_or_404
from rest_framework import filters, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.permissions import HasModulePermission

from .models import Role, User
from .serializers import (
    AssignPermissionSerializer,
    AssignRoleSerializer,
    ModuleRightSerializer,
    RoleSerializer,
    UserSerializer,
    UserWriteSerializer,
)
from .services import assign_permission_to_role, assign_role_to_user


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
        role = assign_role_to_user(user, serializer.validated_data["role_name"])
        return Response(
            {
                "message": f"Role '{role.name}' assigned.",
                "data": {"user_id": user.id, "role": role.name},
            },
            status=status.HTTP_200_OK,
        )


class RoleViewSet(ModelViewSet):
    """CRUD for roles — admin only.

    GET    /api/accounts/roles/
    POST   /api/accounts/roles/
    GET    /api/accounts/roles/<id>/
    POST   /api/accounts/roles/<id>/assign-permission/
    """

    queryset = Role.objects.prefetch_related("rights", "users").all()
    permission_classes = [IsAuthenticated, HasAccountsPermission]
    serializer_class = RoleSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

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
                "message": "Role created.",
                "data": RoleSerializer(role).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        # Per UC018: role privileges should not be modified after creation.
        # We allow updating description only (additive).
        kwargs.pop("partial", False)
        instance = self.get_object()
        if instance.is_frozen and "description" in request.data:
            instance.description = request.data["description"]
            instance.save(update_fields=["description", "updated_at"])
            return Response(
                {
                    "message": "Role description updated (frozen role — only description editable).",
                    "data": RoleSerializer(instance).data,
                },
                status=status.HTTP_200_OK,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_frozen:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Cannot delete a frozen role.",
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
                        "message": "Cannot delete a role that has users assigned.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        instance.delete()
        return Response(
            {"message": "Role deleted.", "data": {}},
            status=status.HTTP_200_OK,
        )


class AssignPermissionView(APIView):
    """POST /api/accounts/roles/<id>/assign-permission/ — additive only."""

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
        serializer = AssignPermissionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        right = assign_permission_to_role(
            role,
            serializer.validated_data["module"],
            serializer.validated_data["action"],
        )
        return Response(
            {
                "message": "Permission assigned (additive).",
                "data": ModuleRightSerializer(right).data,
            },
            status=status.HTTP_201_CREATED,
        )

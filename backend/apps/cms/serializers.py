"""Serializers for the CMS module."""

from rest_framework import serializers

from .models import Banner, MenuItem, Page


class PageSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = Page
        fields = [
            "id",
            "title",
            "slug",
            "body",
            "meta_description",
            "status",
            "order",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_name", "created_at", "updated_at"]


class PageListSerializer(serializers.ModelSerializer):
    """Lighter serializer for list views."""

    class Meta:
        model = Page
        fields = ["id", "title", "slug", "status", "order", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class BannerSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(
        source="created_by.full_name", read_only=True, default=None
    )

    class Meta:
        model = Banner
        fields = [
            "id",
            "title",
            "subtitle",
            "body",
            "image",
            "link_url",
            "link_text",
            "position",
            "is_active",
            "order",
            "starts_at",
            "ends_at",
            "created_by",
            "created_by_name",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "created_by_name", "created_at", "updated_at"]


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            "id",
            "label",
            "url",
            "location",
            "order",
            "is_active",
            "opens_new_tab",
            "parent",
        ]
        read_only_fields = ["id"]

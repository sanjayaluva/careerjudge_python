"""Upload URLs — included at /api/uploads/ (Signed Doc 3 §2.1.2)."""

from django.urls import re_path

from .uploads import EditorImageUploadView, EditorImageView

urlpatterns = [
    re_path(r"^editor-images/$", EditorImageUploadView.as_view(), name="editor-image-upload"),
    re_path(
        r"^editor-images/(?P<filename>[0-9a-f]{32}\.(?:png|jpg|gif|webp))$",
        EditorImageView.as_view(),
        name="editor-image",
    ),
]

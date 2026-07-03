"""Views for question child resources (options, media, flash items, hotspots).

These are nested under questions: /api/question-bank/questions/<question_id>/options/ etc.
"""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from core.permissions import HasModulePermission

from .models import (
    CorrectAnswer,
    FlashItem,
    HotspotArea,
    MediaFile,
    Question,
    ResponseOption,
)
from .serializers import (
    FlashItemSerializer,
    HotspotAreaSerializer,
    MediaFileSerializer,
    ResponseOptionSerializer,
)


class HasQBPermission(HasModulePermission):
    module = "question_bank"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
    }


# ---------------------------------------------------------------------------
# ResponseOption CRUD (nested under Question)
# ---------------------------------------------------------------------------


class ResponseOptionViewSet(ModelViewSet):
    """CRUD for response options on a question.

    GET    /api/question-bank/questions/<qid>/options/
    POST   /api/question-bank/questions/<qid>/options/
    GET    /api/question-bank/questions/<qid>/options/<id>/
    PATCH  /api/question-bank/questions/<qid>/options/<id>/
    DELETE /api/question-bank/questions/<qid>/options/<id>/
    """

    serializer_class = ResponseOptionSerializer
    permission_classes = [IsAuthenticated, HasQBPermission]

    def get_queryset(self):
        qid = self.kwargs.get("question_id")
        return ResponseOption.objects.filter(question_id=qid)

    def perform_create(self, serializer):
        qid = self.kwargs.get("question_id")
        question = get_object_or_404(Question, id=qid)
        serializer.save(question=question)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response({"message": "OK", "data": serializer.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Option created.",
                "data": ResponseOptionSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Option updated.", "data": ResponseOptionSerializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Option deleted.", "data": {}}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Bulk save options (create + update + delete in one request)
# ---------------------------------------------------------------------------


class BulkOptionsView(APIView):
    """POST /api/question-bank/questions/<qid>/options/bulk/

    Accepts a full list of options and syncs them to the DB:
    - New options (no id) are created
    - Existing options (with id) are updated
    - Options not in the list are deleted

    Request body: { "options": [ { ... }, { ... } ] }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, question_id):
        if not request.user.has_module_right("question_bank", "add"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You do not have permission to manage question options.",
                        "details": {},
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        question = get_object_or_404(Question, id=question_id)
        submitted = request.data.get("options", [])
        # Tracks the IDs of all options that should be kept (both updated and newly created).
        # Options not in this set at the end of the loop are deleted (line ~190).
        kept_ids = set()

        for opt_data in submitted:
            # Extract correct_answers (FITB) — handle separately (not a model field on ResponseOption)
            correct_answers_data = opt_data.pop("correct_answers", None)

            opt_id = opt_data.get("id")
            if opt_id:
                # Update existing
                try:
                    opt = ResponseOption.objects.get(id=opt_id, question=question)
                    serializer = ResponseOptionSerializer(opt, data=opt_data, partial=True)
                    serializer.is_valid(raise_exception=True)
                    serializer.save()
                    kept_ids.add(opt.id)
                except ResponseOption.DoesNotExist:
                    # ID provided but not found for this question — create new instead
                    clean_data = {k: v for k, v in opt_data.items() if k != "id"}
                    serializer = ResponseOptionSerializer(data=clean_data)
                    serializer.is_valid(raise_exception=True)
                    serializer.save(question=question)
                    opt = serializer.instance
                    kept_ids.add(opt.id)
            else:
                # Create new
                clean_data = {k: v for k, v in opt_data.items() if k != "id"}
                serializer = ResponseOptionSerializer(data=clean_data)
                serializer.is_valid(raise_exception=True)
                serializer.save(question=question)
                opt = serializer.instance
                kept_ids.add(opt.id)  # CRITICAL: track newly-created option IDs too

            # Save correct answers for FITB types
            if correct_answers_data and opt:
                # Delete existing correct answers for this option
                opt.correct_answers.all().delete()
                for ca in correct_answers_data:
                    answer_text = ca.get("answer_text", "") if isinstance(ca, dict) else str(ca)
                    if answer_text:
                        CorrectAnswer.objects.create(
                            response_option=opt,
                            answer_text=answer_text,
                            order=ca.get("order", 0) if isinstance(ca, dict) else 0,
                        )

        # Delete options not in the submitted list (i.e. removed by the user in the editor)
        ResponseOption.objects.filter(question=question).exclude(id__in=kept_ids).delete()

        # Return all current options
        all_options = ResponseOption.objects.filter(question=question)
        return Response(
            {
                "message": f"Saved {all_options.count()} options.",
                "data": ResponseOptionSerializer(all_options, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# MediaFile CRUD (nested under Question)
# ---------------------------------------------------------------------------


class MediaFileViewSet(ModelViewSet):
    """CRUD for media files on a question.

    GET    /api/question-bank/questions/<qid>/media/
    POST   /api/question-bank/questions/<qid>/media/
    DELETE /api/question-bank/questions/<qid>/media/<id>/
    """

    serializer_class = MediaFileSerializer
    permission_classes = [IsAuthenticated, HasQBPermission]

    def get_queryset(self):
        qid = self.kwargs.get("question_id")
        return MediaFile.objects.filter(question_id=qid)

    def perform_create(self, serializer):
        qid = self.kwargs.get("question_id")
        question = get_object_or_404(Question, id=qid)
        serializer.save(question=question)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Media file added.", "data": MediaFileSerializer(serializer.instance).data},
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Media file deleted.", "data": {}}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# FlashItem CRUD (nested under Question)
# ---------------------------------------------------------------------------


class FlashItemViewSet(ModelViewSet):
    """CRUD for flash items on a question.

    GET    /api/question-bank/questions/<qid>/flash-items/
    POST   /api/question-bank/questions/<qid>/flash-items/
    DELETE /api/question-bank/questions/<qid>/flash-items/<id>/
    """

    serializer_class = FlashItemSerializer
    permission_classes = [IsAuthenticated, HasQBPermission]

    def get_queryset(self):
        qid = self.kwargs.get("question_id")
        return FlashItem.objects.filter(question_id=qid)

    def perform_create(self, serializer):
        qid = self.kwargs.get("question_id")
        question = get_object_or_404(Question, id=qid)
        serializer.save(question=question)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Flash item added.", "data": FlashItemSerializer(serializer.instance).data},
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Flash item deleted.", "data": {}}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# HotspotArea CRUD (nested under Question)
# ---------------------------------------------------------------------------


class HotspotAreaViewSet(ModelViewSet):
    """CRUD for hotspot areas on a question.

    GET    /api/question-bank/questions/<qid>/hotspots/
    POST   /api/question-bank/questions/<qid>/hotspots/
    DELETE /api/question-bank/questions/<qid>/hotspots/<id>/
    """

    serializer_class = HotspotAreaSerializer
    permission_classes = [IsAuthenticated, HasQBPermission]

    def get_queryset(self):
        qid = self.kwargs.get("question_id")
        return HotspotArea.objects.filter(question_id=qid)

    def perform_create(self, serializer):
        qid = self.kwargs.get("question_id")
        question = get_object_or_404(Question, id=qid)
        serializer.save(question=question)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {
                "message": "Hotspot area added.",
                "data": HotspotAreaSerializer(serializer.instance).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response({"message": "Hotspot area deleted.", "data": {}}, status=status.HTTP_200_OK)

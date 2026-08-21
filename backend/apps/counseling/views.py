"""Views for the Counseling module.

Endpoints:
  GET/POST  /api/counseling/categories/                  — list/create categories
  GET/POST  /api/counseling/counsellors/                  — list counsellors
  GET/PATCH /api/counseling/counsellors/<id>/             — retrieve/update profile
  GET/POST  /api/counseling/timeslots/                    — list/create timeslots
  GET       /api/counseling/counsellors/<id>/timeslots/   — list counsellor's slots
  GET/POST  /api/counseling/sessions/                     — list/book sessions
  GET/PATCH /api/counseling/sessions/<id>/                — retrieve/update session
  POST      /api/counseling/sessions/<id>/confirm/        — counsellor confirms
  POST      /api/counseling/sessions/<id>/cancel/         — cancel with refund logic
  POST      /api/counseling/sessions/<id>/complete/       — mark session completed
  GET/POST  /api/counseling/sessions/<id>/summary/        — counsellor's post-session notes
  GET/POST  /api/counseling/sessions/<id>/feedback/       — counselee's feedback
  GET/POST  /api/counseling/sessions/<id>/followups/      — propose follow-up
  POST      /api/counseling/followups/<id>/confirm/       — counselee confirms follow-up
  GET       /api/counseling/my-sessions/                  — counselee's own sessions
"""

from datetime import timedelta

from django.utils import timezone
from rest_framework import filters, serializers, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from core.mixins import ActionSerializerMixin
from core.permissions import HasModulePermission

from .models import (
    CounselingCategory,
    CounselingSession,
    CounselingSettings,
    CounsellorProfile,
    FollowupSession,
    SessionCancellation,
    SessionFeedback,
    SessionSummary,
    TimeSlot,
)
from .serializers import (
    CounselingCategorySerializer,
    CounselingSessionSerializer,
    CounsellorProfileSerializer,
    FollowupSessionSerializer,
    SessionCancellationSerializer,
    SessionFeedbackSerializer,
    SessionSummarySerializer,
    TimeSlotSerializer,
)


class HasCounselingPermission(HasModulePermission):
    module = "counseling"
    action_map = {
        "list": "view",
        "retrieve": "view",
        "create": "add",
        "update": "change",
        "partial_update": "change",
        "destroy": "delete",
        "timeslots": "view",
        "confirm": "change",
        "cancel": "change",
        "complete": "change",
        "summary": "change",
        "feedback": "add",  # counselee submits feedback
        "followups": "change",
        "confirm_followup": "add",
        "my_sessions": "view",
    }


# ---------------------------------------------------------------------------
# Category ViewSet
# ---------------------------------------------------------------------------


class CounselingCategoryViewSet(ActionSerializerMixin, ModelViewSet):
    queryset = CounselingCategory.objects.all()
    permission_classes = [IsAuthenticated, HasCounselingPermission]
    serializer_class = CounselingCategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name", "description"]

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {"message": "OK", "data": self.get_serializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Category created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# Counsellor Profile ViewSet
# ---------------------------------------------------------------------------


class CounsellorProfileViewSet(ActionSerializerMixin, ModelViewSet):
    queryset = CounsellorProfile.objects.select_related("user", "user__profile").prefetch_related(
        "categories", "timeslots"
    )
    permission_classes = [IsAuthenticated, HasCounselingPermission]
    serializer_class = CounsellorProfileSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["user__full_name", "user__email", "user__profile__bio"]
    ordering_fields = ["created_at", "user__full_name"]
    ordering = ["user__full_name"]

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if category := params.get("category"):
            qs = qs.filter(categories__name=category)
        if available := params.get("available"):
            qs = qs.filter(is_available=available == "true")
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return Response({"message": "OK", "data": resp.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {"message": "OK", "data": self.get_serializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(
            {"message": "Counsellor profile created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def timeslots(self, request, pk=None):
        """List a counsellor's available timeslots (SRS §2.1: 'System shows
        available timeslots of the counsellor for a week')."""
        counsellor = self.get_object()
        # Default: show slots from now to 3 weeks ahead (SRS §3.1 max)
        weeks = int(request.query_params.get("weeks", 3))
        from_date = timezone.now()
        to_date = from_date + timedelta(weeks=weeks)
        slots = counsellor.timeslots.filter(
            start_time__gte=from_date, start_time__lte=to_date
        ).order_by("start_time")
        return Response(
            {"message": "OK", "data": TimeSlotSerializer(slots, many=True).data},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# TimeSlot ViewSet
# ---------------------------------------------------------------------------


class TimeSlotViewSet(ModelViewSet):
    queryset = TimeSlot.objects.select_related("counsellor")
    permission_classes = [IsAuthenticated, HasCounselingPermission]
    serializer_class = TimeSlotSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if counsellor := params.get("counsellor"):
            qs = qs.filter(counsellor_id=counsellor)
        if status_filter := params.get("status"):
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        # Only the counsellor themselves or admin can create timeslots
        counsellor_id = serializer.validated_data.get("counsellor")
        counsellor = CounsellorProfile.objects.filter(id=counsellor_id.id).first()
        user_role_name = self.request.user.role.name if self.request.user.role_id else None
        if (
            counsellor
            and counsellor.user_id != self.request.user.id
            and user_role_name != "cj_admin"
        ):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You can only manage your own timeslots.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer.save()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # Permission check
        counsellor = serializer.validated_data["counsellor"]
        user_role_name = request.user.role.name if request.user.role_id else None
        if counsellor.user_id != request.user.id and user_role_name != "cj_admin":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You can only manage your own timeslots.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        # Report 3 §1.2: enforce max-weeks-ahead limit (admin-configurable).

        max_weeks = CounselingSettings.get().max_weeks_ahead
        start = serializer.validated_data.get("start_time")
        if start:
            from datetime import timedelta

            from django.utils import timezone

            horizon = timezone.now() + timedelta(weeks=max_weeks)
            # Allow naive datetimes from the serializer to slip through; only
            # compare when both sides are aware (or coerce).
            try:
                if timezone.is_aware(start) and start > horizon:
                    raise ValueError
                if not timezone.is_aware(start):
                    start_aware = timezone.make_aware(start) if start > timezone.now() else start
                    if timezone.is_aware(start_aware) and start_aware > horizon:
                        raise ValueError
            except ValueError:
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": (
                                f"Timeslots cannot be more than {max_weeks} weeks ahead "
                                f"(admin-configurable limit)."
                            ),
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        serializer.save()
        return Response(
            {"message": "Time slot created.", "data": serializer.data},
            status=status.HTTP_201_CREATED,
        )

    def _check_ownership(self, instance):
        """Only the counsellor who owns the slot (or an admin) may modify/delete it."""
        user_role_name = self.request.user.role.name if self.request.user.role_id else None
        return instance.counsellor.user_id == self.request.user.id or user_role_name == "cj_admin"

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._check_ownership(instance):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You can only manage your own timeslots.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._check_ownership(instance):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You can only manage your own timeslots.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not self._check_ownership(instance):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "You can only manage your own timeslots.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        # Report 3 §1.1: block editing/deleting a slot that's already booked.
        if instance.status == "booked":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Cannot delete a timeslot that is already booked.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)


# ---------------------------------------------------------------------------
# Session ViewSet (booking + confirm + cancel + complete + summary + feedback)
# ---------------------------------------------------------------------------


class CounselingSessionViewSet(ModelViewSet):
    queryset = CounselingSession.objects.select_related(
        "counselee", "counsellor", "category", "timeslot"
    )
    permission_classes = [IsAuthenticated, HasCounselingPermission]
    serializer_class = CounselingSessionSerializer
    http_method_names = ["get", "head", "options", "post", "patch"]

    def get_queryset(self):
        user = self.request.user
        user_role_name = user.role.name if user.role_id else None
        qs = super().get_queryset()
        # Counselees see only their own sessions
        if user_role_name in ("individual",):
            return qs.filter(counselee=user)
        # Counsellors see sessions booked with them
        if user_role_name == "counsellor":
            try:
                profile = user.counsellor_profile
                return qs.filter(counsellor=profile)
            except CounsellorProfile.DoesNotExist:
                return qs.none()
        # Admin + helpdesk see all
        return qs

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(
            {"message": "OK", "data": self.get_serializer(instance).data},
            status=status.HTTP_200_OK,
        )

    def create(self, request, *args, **kwargs):
        """Book a counselling session (SRS §2.1, Report 3 §1.8/§1.10).

        Body:
            {
                "counsellor": 42,
                "timeslot": 10,
                "category": 1,
                "topic": "Career advice",
                "description": "...",
                "mode": "online",
                "terms_accepted": true
            }

        Creates a pending session + marks the timeslot as booked.
        The counselee is the authenticated user. Per Report 3 §1.8 the
        counselee must accept the terms; per §1.10 the counsellor + helpdesk
        are notified of the new booking.
        """
        # Report 3 §1.8: terms must be explicitly accepted.
        if not request.data.get("terms_accepted"):
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "You must accept the Terms & Conditions to book.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Validate the timeslot is available
        timeslot = serializer.validated_data["timeslot"]
        if timeslot.status != "available":
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "This time slot is no longer available.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        counsellor = serializer.validated_data["counsellor"]
        # Capture the fee at booking time
        session = serializer.save(
            counselee=request.user,
            fee=counsellor.hourly_rate,
            status="pending",
            payment_status="pending",
            terms_accepted=True,
        )
        # Mark the timeslot as booked
        timeslot.status = "booked"
        timeslot.save(update_fields=["status"])

        # Report 3 §1.10: notify the counsellor + helpdesk of the new booking.
        from apps.notifications.models import notify_role, notify_user

        counselee_name = request.user.full_name or request.user.email
        slot_str = timeslot.start_time.strftime("%Y-%m-%d %H:%M")
        notify_user(
            counsellor.user,
            f"New booking: {counselee_name}",
            f"{counselee_name} booked a session for {slot_str}. "
            f"Topic: {session.topic}. Please confirm within the confirm window.",
            "session",
            f"/counseling?session={session.id}",
        )
        notify_role(
            "helpdesk",
            f"New counselling booking: {counselee_name}",
            f"{counselee_name} booked a session with {counsellor.full_name} on {slot_str}.",
            "session",
        )

        return Response(
            {
                "message": "Session booked. Awaiting counsellor confirmation.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Counsellor confirms a pending session (SRS §3.2)."""
        session = self.get_object()
        if session.status != "pending":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Cannot confirm a session with status '{session.status}'.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        session.status = "confirmed"
        session.confirmed_at = timezone.now()
        session.save(update_fields=["status", "confirmed_at"])
        return Response(
            {"message": "Session confirmed.", "data": CounselingSessionSerializer(session).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        """Cancel a session with refund logic (SRS §2.2, Report 3 §1.15/§1.16).

        Refund rules (thresholds admin-configurable via CounselingSettings):
          - > full_refund_within_hours (default 24) before: full refund
          - > half_refund_within_hours (default 4) before: 50% refund
          - less: no refund

        Body: {"reason": "...", "cancelled_by": "counselee" | "counsellor"}
        Only the session's counselee, its counsellor, or an admin may cancel.
        """
        session = self.get_object()
        if session.status in ("cancelled", "completed"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Cannot cancel a session with status '{session.status}'.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Only the counselee, the counsellor, or an admin may cancel.
        user_role_name = request.user.role.name if request.user.role_id else None
        is_admin = user_role_name == "cj_admin" or request.user.is_superuser
        is_counselee = session.counselee_id == request.user.id
        is_counsellor = session.counsellor.user_id == request.user.id
        if not (is_admin or is_counselee or is_counsellor):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the counselee, the counsellor, or an admin can cancel.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Infer cancelled_by from the caller when not explicitly provided.
        default_by = "counsellor" if is_counsellor and not is_counselee else "counselee"
        cancelled_by = request.data.get("cancelled_by", default_by)
        reason = request.data.get("reason", "")

        # Report 3 §1.16: reason is required for cancellations.
        if not reason.strip():
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "A reason is required to cancel.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Compute refund tier based on time until session (admin-configurable).
        settings = CounselingSettings.get()
        now = timezone.now()
        session_time = session.timeslot.start_time
        hours_until = (session_time - now).total_seconds() / 3600

        if hours_until >= settings.full_refund_within_hours:
            refund_tier = "full"
            refund_amount = session.fee
        elif hours_until >= settings.half_refund_within_hours:
            refund_tier = "half"
            refund_amount = session.fee / 2
        else:
            refund_tier = "none"
            refund_amount = 0

        # Create cancellation record
        cancellation = SessionCancellation.objects.create(
            session=session,
            cancelled_by=cancelled_by,
            reason=reason,
            refund_tier=refund_tier,
            refund_amount=refund_amount,
        )

        # Update session status
        session.status = "cancelled"
        session.payment_status = f"refunded_{refund_tier}"
        session.save(update_fields=["status", "payment_status"])

        # Free up the timeslot
        timeslot = session.timeslot
        timeslot.status = "available"
        timeslot.save(update_fields=["status"])

        # Track counsellor cancellation frequency (SRS §3.2 note)
        if cancelled_by == "counsellor":
            # cancellation_count lives on UserProfile now
            profile = session.counsellor.user.profile
            profile.cancellation_count += 1
            profile.save(update_fields=["cancellation_count"])

        return Response(
            {
                "message": f"Session cancelled. Refund tier: {refund_tier} (${refund_amount}).",
                "data": {
                    "session": CounselingSessionSerializer(session).data,
                    "cancellation": SessionCancellationSerializer(cancellation).data,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        """Mark a session as completed (SRS §3.3: 'End Session')."""
        session = self.get_object()
        if session.status != "confirmed":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Cannot complete a session with status '{session.status}'.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        session.status = "completed"
        session.completed_at = timezone.now()
        session.save(update_fields=["status", "completed_at"])
        return Response(
            {"message": "Session completed.", "data": CounselingSessionSerializer(session).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get", "post"])
    def summary(self, request, pk=None):
        """Counsellor's post-session summary (SRS §3.3).

        GET: retrieve the summary (counsellor + admin only)
        POST: create/update the summary
        """
        session = self.get_object()
        if request.method == "GET":
            if not hasattr(session, "summary"):
                return Response(
                    {"message": "OK", "data": None},
                    status=status.HTTP_200_OK,
                )
            return Response(
                {"message": "OK", "data": SessionSummarySerializer(session.summary).data},
                status=status.HTTP_200_OK,
            )
        # POST: create or update (Report 3 §2.4 — 6 summary fields)
        summary, _ = SessionSummary.objects.update_or_create(
            session=session,
            defaults={
                "counsellor": request.user,
                "client_details": request.data.get("client_details", ""),
                "summary": request.data.get("summary", ""),
                "provisional_diagnosis": request.data.get("provisional_diagnosis", ""),
                "case_prognosis": request.data.get("case_prognosis", ""),
                "session_smoothness": request.data.get("session_smoothness", ""),
                "smoothness_reason": request.data.get("smoothness_reason", ""),
                "followup_recommended": bool(request.data.get("followup_recommended", False)),
                # legacy
                "recommendations": request.data.get("recommendations", ""),
            },
        )
        return Response(
            {"message": "Summary saved.", "data": SessionSummarySerializer(summary).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def feedback(self, request, pk=None):
        """Counselee's feedback (SRS §2.3).

        Per SRS: "User feedbacks are available only to Admin User."
        Counselees can submit their own feedback but can only view their own.
        """
        session = self.get_object()
        if request.method == "GET":
            # Only admin can view all feedback; counselee can view their own
            user_role_name = request.user.role.name if request.user.role_id else None
            if user_role_name != "cj_admin" and session.counselee_id != request.user.id:
                return Response(
                    {"error": {"code": "forbidden", "message": "Feedback is admin-only."}},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if not hasattr(session, "feedback"):
                return Response({"message": "OK", "data": None}, status=status.HTTP_200_OK)
            return Response(
                {"message": "OK", "data": SessionFeedbackSerializer(session.feedback).data},
                status=status.HTTP_200_OK,
            )
        # POST: counselee submits feedback
        if session.counselee_id != request.user.id:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the counselee can submit feedback.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if session.status != "completed":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Feedback can only be submitted after session completion.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        feedback, _ = SessionFeedback.objects.update_or_create(
            session=session,
            defaults={
                "counselee": request.user,
                # Report 3 §2.2 — 8 feedback fields
                "session_usefulness": request.data.get("session_usefulness", ""),
                "usefulness_text": request.data.get("usefulness_text", ""),
                "counsellor_empathy": request.data.get("counsellor_empathy", ""),
                "session_ending": request.data.get("session_ending", ""),
                "would_rechoose": request.data.get("would_rechoose", ""),
                "rechoose_text": request.data.get("rechoose_text", ""),
                "improvement_suggestions": request.data.get("improvement_suggestions", ""),
                "counsellor_rating": int(request.data.get("rating", 5)),
                "rating": int(request.data.get("rating", 5)),
                # legacy
                "experience_text": request.data.get("experience_text", ""),
                "counsellor_effectiveness": request.data.get("counsellor_effectiveness", ""),
            },
        )
        return Response(
            {"message": "Feedback submitted.", "data": SessionFeedbackSerializer(feedback).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "post"])
    def followups(self, request, pk=None):
        """Propose a follow-up session (SRS §3.3).

        POST body: {"proposed_time": "2026-08-15T10:00:00Z"}
        """
        session = self.get_object()
        if request.method == "GET":
            followups = session.followups.all()
            return Response(
                {"message": "OK", "data": FollowupSessionSerializer(followups, many=True).data},
                status=status.HTTP_200_OK,
            )
        # POST: counsellor proposes a follow-up
        proposed_time = request.data.get("proposed_time")
        if not proposed_time:
            return Response(
                {"error": {"code": "validation_error", "message": "proposed_time is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        followup = FollowupSession.objects.create(
            original_session=session,
            counsellor=session.counsellor,
            proposed_time=proposed_time,
            status="proposed",
        )
        return Response(
            {"message": "Follow-up proposed.", "data": FollowupSessionSerializer(followup).data},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def my_sessions(self, request):
        """Counselee views their own sessions."""
        sessions = self.get_queryset().filter(counselee=request.user)
        return Response(
            {"message": "OK", "data": CounselingSessionSerializer(sessions, many=True).data},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# FollowupSession ViewSet (confirm follow-up — SRS §3.3)
# ---------------------------------------------------------------------------


class FollowupSessionViewSet(ModelViewSet):
    queryset = FollowupSession.objects.select_related(
        "original_session", "counsellor", "confirmed_session"
    )
    permission_classes = [IsAuthenticated, HasCounselingPermission]
    serializer_class = FollowupSessionSerializer
    http_method_names = ["get", "head", "options", "post", "patch"]

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Counselee confirms a follow-up session (SRS §3.3).

        Per SRS: "User initiates payment and confirms appointment."
        Creates a new CounselingSession with status='confirmed'.
        """
        followup = self.get_object()
        if followup.status != "proposed":
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Cannot confirm a follow-up with status '{followup.status}'.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        # Create a timeslot for the follow-up
        timeslot = TimeSlot.objects.create(
            counsellor=followup.counsellor,
            start_time=followup.proposed_time,
            end_time=followup.proposed_time + timedelta(hours=1),
            status="booked",
        )
        # Create the new session
        original = followup.original_session
        new_session = CounselingSession.objects.create(
            counselee=request.user,
            counsellor=followup.counsellor,
            category=original.category,
            timeslot=timeslot,
            topic=f"Follow-up: {original.topic}",
            description="Follow-up session",
            terms_accepted=True,
            status="confirmed",
            payment_status="paid",  # Assume payment done
            mode=original.mode,
            fee=followup.counsellor.hourly_rate,
            confirmed_at=timezone.now(),
        )
        followup.confirmed_session = new_session
        followup.status = "confirmed"
        followup.save(update_fields=["confirmed_session", "status"])
        return Response(
            {
                "message": "Follow-up confirmed.",
                "data": {
                    "followup": FollowupSessionSerializer(followup).data,
                    "session": CounselingSessionSerializer(new_session).data,
                },
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def decline(self, request, pk=None):
        """Counselee declines a follow-up session."""
        followup = self.get_object()
        followup.status = "declined"
        followup.save(update_fields=["status"])
        return Response(
            {"message": "Follow-up declined.", "data": FollowupSessionSerializer(followup).data},
            status=status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Report 3 §1.9/§1.11/§1.2/§1.12 — global counseling settings (admin-only)
# ---------------------------------------------------------------------------


class CounselingSettingsViewSet(ViewSet):
    """Retrieve or update the counseling-module settings singleton
    (terms & conditions, refund policy, max_weeks_ahead, confirm window,
    refund thresholds).

    GET    /api/counseling/settings/        — any authenticated user (so the
                                              booking form can show terms)
    PATCH  /api/counseling/settings/        — cj_admin only.
    """

    permission_classes = [IsAuthenticated, HasCounselingPermission]

    def list(self, request):

        return Response(
            {"message": "OK", "data": _CounselingSettingsData(CounselingSettings.get()).data},
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, pk=None):
        # Treat as a singleton — pk ignored; same as list.
        return self.list(request)

    def partial_update(self, request, pk=None):
        user_role_name = request.user.role.name if request.user.role_id else None
        if user_role_name != "cj_admin" and not request.user.is_superuser:
            return Response(
                {"error": {"code": "forbidden", "message": "Only CJ Admin can edit settings."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        settings = CounselingSettings.get()
        serializer = _CounselingSettingsData(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Settings updated.", "data": serializer.data},
            status=status.HTTP_200_OK,
        )


class _CounselingSettingsData(serializers.ModelSerializer):
    """Lightweight serializer for the settings singleton (defined here to keep
    the view + serializer together)."""

    class Meta:
        model = CounselingSettings
        fields = [
            "terms_and_conditions",
            "cancellation_policy",
            "max_weeks_ahead",
            "confirm_window_hours",
            "full_refund_within_hours",
            "half_refund_within_hours",
        ]

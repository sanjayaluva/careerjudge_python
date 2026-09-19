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

# D8 §2.3: join-window bounds around the timeslot's scheduled start/end —
# mirrors frontend/src/pages/counseling/joinWindow.ts JOIN_WINDOW_BEFORE_MIN /
# JOIN_WINDOW_AFTER_END_MIN. Keep both in sync.
JOIN_WINDOW_BEFORE_MIN = 10
JOIN_WINDOW_AFTER_END_MIN = 15


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
        # H16/D8 §2.3: counsellor sets the per-session meeting link.
        "meeting_link": "change",
        # D8: any participant (counselee/counsellor) may join within the
        # window — gated at 'view' so it doesn't require write access.
        "join": "view",
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
        available timeslots of the counsellor for a week').

        Query params:
          weeks=N        — cumulative window: now .. now + N weeks (default
                            behaviour, kept for backward compatibility).
          week_offset=N   — dossier gap D8 "browse future weeks": a single
                            calendar week window, N weeks from now (0 = this
                            week, 1 = next week, etc). When given, overrides
                            `weeks` and returns just that one week's slots so
                            the UI can page forward/backward through future
                            weeks instead of always getting the cumulative
                            list. Capped at CounselingSettings.max_weeks_ahead
                            (the same limit timeslot creation enforces).
        """
        counsellor = self.get_object()
        now = timezone.now()
        week_offset = request.query_params.get("week_offset")
        if week_offset is not None:
            try:
                offset = max(0, int(week_offset))
            except ValueError:
                return Response(
                    {
                        "error": {
                            "code": "validation_error",
                            "message": "week_offset must be an integer.",
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            max_weeks = CounselingSettings.get().max_weeks_ahead
            offset = min(offset, max_weeks)
            from_date = now + timedelta(weeks=offset)
            to_date = from_date + timedelta(weeks=1)
        else:
            # Default: show slots from now to N weeks ahead (SRS §3.1 max 3)
            weeks = int(request.query_params.get("weeks", 3))
            from_date = now
            to_date = from_date + timedelta(weeks=weeks)
        slots = counsellor.timeslots.filter(
            start_time__gte=from_date, start_time__lte=to_date
        ).order_by("start_time")
        return Response(
            {
                "message": "OK",
                "data": TimeSlotSerializer(slots, many=True).data,
                "week_start": from_date.isoformat(),
                "week_end": to_date.isoformat(),
            },
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
        fee = counsellor.hourly_rate
        # H15/D8 §2.1: a session is only 'paid' once the gateway/webhook says
        # so — free sessions (fee=0) are the one exception, auto-marked paid
        # exactly like free training courses (apps/training/views.py register()).
        is_free = float(fee) == 0
        session = serializer.save(
            counselee=request.user,
            fee=fee,
            status="pending",
            payment_status="paid" if is_free else "pending",
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

        # H15/D8 §2.1/§3.3: route payment through the gateway — same pattern
        # as apps/training/views.py CourseViewSet.register(). The webhook
        # (apps/payments/services.py _update_module_payment_status) flips
        # session.payment_status to 'paid'; nothing here assumes payment done.
        from apps.payments.services import create_stripe_checkout_session, get_or_create_payment

        payment = get_or_create_payment(
            request.user,
            module="counseling",
            item_id=session.id,
            amount=fee,
            description=f"Counselling session with {counsellor.full_name}",
        )
        checkout_url = None
        if not is_free:
            success_url = request.build_absolute_uri("/counseling?payment=success")
            cancel_url = request.build_absolute_uri("/counseling?payment=cancelled")
            checkout_url = create_stripe_checkout_session(payment, success_url, cancel_url)

        if is_free:
            message = "Session booked. Awaiting counsellor confirmation."
        elif checkout_url is None:
            message = "Session booked. Complete payment to confirm your session."
        else:
            message = "Session booked. Redirecting to payment…"

        return Response(
            {
                "message": message,
                "data": {**serializer.data, "checkout_url": checkout_url},
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

        # Dossier gap D8: execute the refund through the payments module
        # rather than only recording it here. A full Stripe gateway refund
        # is attempted when configured; either way, the Payment record is
        # flipped to 'refunded' so it's reflected in the system of record.
        refund_executed = False
        if refund_amount and float(refund_amount) > 0:
            from apps.payments.models import Payment
            from apps.payments.services import refund_payment

            payment = Payment.objects.filter(module="counseling", item_id=session.id).first()
            if payment:
                refund_executed = refund_payment(payment, amount=refund_amount)

        # Create cancellation record
        cancellation = SessionCancellation.objects.create(
            session=session,
            cancelled_by=cancelled_by,
            reason=reason,
            refund_tier=refund_tier,
            refund_amount=refund_amount,
            refund_executed=refund_executed,
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
        now = timezone.now()
        session.completed_at = now
        update_fields = ["status", "completed_at"]
        # D8: record the actual end of the live delivery, distinct from the
        # scheduled timeslot end. Only set if not already recorded (e.g. via
        # a future explicit "leave" action) so completion never overwrites it.
        if not session.actual_end_at:
            session.actual_end_at = now
            update_fields.append("actual_end_at")
        session.save(update_fields=update_fields)
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
            # Only the counsellor (owner) or admin can view the summary; a
            # counselee must never see counsellor-private notes (D8 §3.3).
            user_role_name = request.user.role.name if request.user.role_id else None
            if user_role_name != "cj_admin" and (
                not session.counsellor_id or session.counsellor.user_id != request.user.id
            ):
                return Response(
                    {
                        "error": {
                            "code": "forbidden",
                            "message": "Summary is counsellor/admin-only.",
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )
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
        Counselees can submit their own feedback but cannot read it back
        (CNS-8: viewing is Admin-only per the signed rule).
        """
        session = self.get_object()
        if request.method == "GET":
            # SRS §2.3: feedback is viewable only by the CJ Admin.
            user_role_name = request.user.role.name if request.user.role_id else None
            is_admin = user_role_name == "cj_admin" or request.user.is_superuser
            if not is_admin:
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

    @action(detail=True, methods=["post"], url_path="meeting-link")
    def meeting_link(self, request, pk=None):
        """Counsellor sets/updates the per-session meeting link (H16/D8 §2.3).

        Body: {"meeting_link": "https://zoom.us/j/..."}
        Only the session's own counsellor (or an admin) may set it — this is
        what the live-delivery Join-Session button on both dashboards links
        to, gated by a countdown to the timeslot's start time.
        """
        session = self.get_object()
        user_role_name = request.user.role.name if request.user.role_id else None
        is_admin = user_role_name == "cj_admin" or request.user.is_superuser
        if not is_admin and session.counsellor.user_id != request.user.id:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the assigned counsellor can set the meeting link.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        session.meeting_link = (request.data.get("meeting_link") or "").strip()
        session.save(update_fields=["meeting_link"])
        return Response(
            {"message": "Meeting link updated.", "data": CounselingSessionSerializer(session).data},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        """Redirect to the per-session meeting link within the join window
        (dossier gap D8: 'provide the redirect to the (per-session) meeting
        link within the join window').

        Only the session's counselee, its counsellor, or an admin may join.
        Enforces the join window server-side (the frontend's countdown is a
        UX affordance, not the source of truth) and records
        `actual_start_at` the first time either party joins — this is the
        "split the session into start/end timestamps" half of D8; `complete`
        records the matching `actual_end_at`.

        Returns the meeting_link for the frontend to redirect/open, plus the
        countdown state so a caller doesn't need to duplicate the math.
        """
        session = self.get_object()
        user_role_name = request.user.role.name if request.user.role_id else None
        is_admin = user_role_name == "cj_admin" or request.user.is_superuser
        is_counselee = session.counselee_id == request.user.id
        is_counsellor = session.counsellor.user_id == request.user.id
        if not (is_admin or is_counselee or is_counsellor):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the counselee, the counsellor, or an admin can join.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if session.status not in ("confirmed", "completed"):
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": f"Cannot join a session with status '{session.status}'.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if session.mode != "online":
            return Response(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Only online sessions have a meeting link to join.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        timeslot = session.timeslot
        now = timezone.now()
        opens_at = timeslot.start_time - timedelta(minutes=JOIN_WINDOW_BEFORE_MIN)
        closes_at = timeslot.end_time + timedelta(minutes=JOIN_WINDOW_AFTER_END_MIN)
        can_join = opens_at <= now <= closes_at
        if not can_join:
            return Response(
                {
                    "error": {
                        "code": "join_window_closed",
                        "message": "The join window for this session is not currently open.",
                    },
                    "data": {"opens_at": opens_at.isoformat(), "closes_at": closes_at.isoformat()},
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        if not session.meeting_link:
            return Response(
                {
                    "error": {
                        "code": "not_ready",
                        "message": "The counsellor hasn't set a meeting link for this session yet.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not session.actual_start_at:
            session.actual_start_at = now
            session.save(update_fields=["actual_start_at"])

        return Response(
            {
                "message": "Join window is open.",
                "data": {
                    "meeting_link": session.meeting_link,
                    "actual_start_at": session.actual_start_at.isoformat(),
                },
            },
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
        # Create the new session. H15/D8 §2.1/§3.3: payment_status must be
        # set by the gateway/webhook, not assumed — mirrors the booking flow
        # in CounselingSessionViewSet.create() above.
        original = followup.original_session
        fee = followup.counsellor.hourly_rate
        is_free = float(fee) == 0
        new_session = CounselingSession.objects.create(
            counselee=request.user,
            counsellor=followup.counsellor,
            category=original.category,
            timeslot=timeslot,
            topic=f"Follow-up: {original.topic}",
            description="Follow-up session",
            terms_accepted=True,
            status="confirmed",
            payment_status="paid" if is_free else "pending",
            mode=original.mode,
            fee=fee,
            confirmed_at=timezone.now(),
        )
        followup.confirmed_session = new_session
        followup.status = "confirmed"
        followup.save(update_fields=["confirmed_session", "status"])

        from apps.payments.services import create_stripe_checkout_session, get_or_create_payment

        payment = get_or_create_payment(
            request.user,
            module="counseling",
            item_id=new_session.id,
            amount=fee,
            description=f"Follow-up session with {followup.counsellor.full_name}",
        )
        checkout_url = None
        if not is_free:
            success_url = request.build_absolute_uri("/counseling?payment=success")
            cancel_url = request.build_absolute_uri("/counseling?payment=cancelled")
            checkout_url = create_stripe_checkout_session(payment, success_url, cancel_url)

        if is_free:
            message = "Follow-up confirmed."
        elif checkout_url is None:
            message = "Follow-up confirmed. Complete payment to finalize."
        else:
            message = "Follow-up confirmed. Redirecting to payment…"

        return Response(
            {
                "message": message,
                "data": {
                    "followup": FollowupSessionSerializer(followup).data,
                    "session": CounselingSessionSerializer(new_session).data,
                    "checkout_url": checkout_url,
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

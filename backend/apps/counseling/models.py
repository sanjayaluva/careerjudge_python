"""Models for the Counseling module.

Per SRS 08_counseling_process.json:
  - End-user (counselee) books counselling sessions
  - Counsellor manages timeslots, confirms/cancels appointments, conducts sessions
  - Helpdesk receives notifications + liaises between parties

Models:
  - CounselingCategory: career, learning, emotional, relationship, etc.
  - CounsellorProfile: counsellor's professional profile + specialties
  - TimeSlot: counsellor's available time slots (per SRS §3.1)
  - CounselingSession: a booked session (counselee + counsellor + timeslot)
  - SessionCancellation: cancellation record with refund tracking (SRS §2.2)
  - SessionSummary: counsellor's post-session notes (SRS §3.3)
  - SessionFeedback: counselee's feedback (SRS §2.3, admin-only)
  - FollowupSession: proposed follow-up session (SRS §3.3)
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class CounselingCategory(models.Model):
    """Counselling category (SRS: career, learning, emotional, etc.)."""

    CATEGORY_CHOICES = [
        ("career", "Career counselling"),
        ("learning", "Learning difficulties"),
        ("emotional", "Emotional problems"),
        ("relationship", "Relationship problems"),
        ("marital", "Marital problems"),
        ("clinical", "Clinical problems"),
        ("health", "Health counselling"),
    ]

    name = models.CharField(_("name"), max_length=20, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("counseling category")
        verbose_name_plural = _("counseling categories")

    def __str__(self) -> str:
        return self.get_name_display()


class CounsellorProfile(models.Model):
    """A counsellor's professional profile (SRS §3).

    This is a lightweight model that links to the user's UserProfile for
    common fields (bio, name, contact info). Only counseling-specific
    data lives here: categories + availability toggle.

    The hourly_rate, meeting_url, is_available, and cancellation_count
    fields now live on UserProfile directly (added in migration) so the
    counsellor manages everything from one profile page.

    This model exists primarily for:
    1. The many-to-many relationship with CounselingCategory
    2. A queryable 'counsellor' entity for the counseling module
    3. Backward compatibility with existing TimeSlot/Session FKs
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="counsellor_profile",
    )
    categories = models.ManyToManyField(CounselingCategory, blank=True, related_name="counsellors")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["user__full_name"]
        verbose_name = _("counsellor profile")
        verbose_name_plural = _("counsellor profiles")

    def __str__(self) -> str:
        return self.user.full_name or self.user.email

    # --- Proxy properties (read from UserProfile so there's one source of truth) ---

    @property
    def full_name(self) -> str:
        return self.user.full_name or self.user.email

    @property
    def bio(self) -> str:
        return getattr(self.user.profile, "bio", "") if hasattr(self.user, "profile") else ""

    @property
    def hourly_rate(self):
        return (
            getattr(self.user.profile, "hourly_rate", 50) if hasattr(self.user, "profile") else 50
        )

    @property
    def meeting_url(self) -> str:
        return (
            getattr(self.user.profile, "meeting_url", "") if hasattr(self.user, "profile") else ""
        )

    @property
    def is_available(self) -> bool:
        return (
            getattr(self.user.profile, "is_available_for_counseling", True)
            if hasattr(self.user, "profile")
            else True
        )

    @property
    def cancellation_count(self) -> int:
        return (
            getattr(self.user.profile, "cancellation_count", 0)
            if hasattr(self.user, "profile")
            else 0
        )


class TimeSlot(models.Model):
    """A counsellor's available time slot (SRS §3.1).

    Counsellors update their timeslots weekly (min 1 week, max 3 weeks ahead).
    Each slot is 1 hour by default. A slot becomes unavailable once booked.
    """

    STATUS_CHOICES = [
        ("available", "Available"),
        ("booked", "Booked (session pending)"),
        ("blocked", "Blocked (counsellor unavailable)"),
    ]

    counsellor = models.ForeignKey(
        CounsellorProfile, on_delete=models.CASCADE, related_name="timeslots"
    )
    start_time = models.DateTimeField(_("start time"))
    end_time = models.DateTimeField(_("end time"))
    status = models.CharField(
        _("status"), max_length=10, choices=STATUS_CHOICES, default="available"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["start_time"]
        verbose_name = _("time slot")
        verbose_name_plural = _("time slots")
        unique_together = [("counsellor", "start_time")]

    def __str__(self) -> str:
        return f"{self.counsellor.full_name} @ {self.start_time:%Y-%m-%d %H:%M}"


class CounselingSession(models.Model):
    """A booked counselling session (SRS §2.1).

    Created when a counselee books a timeslot. Goes through:
      pending → confirmed → completed (or cancelled)
    """

    STATUS_CHOICES = [
        ("pending", "Pending (awaiting counsellor confirmation)"),
        ("confirmed", "Confirmed by counsellor"),
        ("completed", "Session completed"),
        ("cancelled", "Cancelled"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("pending", "Payment Pending"),
        ("paid", "Paid"),
        ("refunded_full", "Refunded (100%)"),
        ("refunded_half", "Refunded (50%)"),
        ("refunded_none", "No refund"),
    ]
    MODE_CHOICES = [
        ("online", "Online (Zoom/Meet)"),
        ("offline", "Offline (in-person)"),
    ]

    counselee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="counseling_sessions_as_counselee",
    )
    counsellor = models.ForeignKey(
        CounsellorProfile, on_delete=models.CASCADE, related_name="sessions"
    )
    category = models.ForeignKey(
        CounselingCategory, on_delete=models.SET_NULL, null=True, blank=True
    )
    timeslot = models.OneToOneField(TimeSlot, on_delete=models.CASCADE, related_name="session")

    # Counselee's topic/issue (SRS §2.1: "topic/issue for counselling")
    topic = models.CharField(_("topic"), max_length=255)
    description = models.TextField(_("description"), blank=True, default="")
    # Terms accepted by the counselee at booking time
    terms_accepted = models.BooleanField(_("terms accepted"), default=False)

    status = models.CharField(_("status"), max_length=15, choices=STATUS_CHOICES, default="pending")
    payment_status = models.CharField(
        _("payment status"),
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
    )
    mode = models.CharField(_("mode"), max_length=10, choices=MODE_CHOICES, default="online")

    # Session fee (captured at booking time — counsellor's hourly_rate)
    fee = models.DecimalField(_("fee"), max_digits=10, decimal_places=2, default=0)

    booked_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(_("confirmed at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)

    class Meta:
        ordering = ["-booked_at"]
        verbose_name = _("counseling session")
        verbose_name_plural = _("counseling sessions")

    def __str__(self) -> str:
        return f"{self.counselee.email} -> {self.counsellor.full_name} ({self.status})"


class SessionCancellation(models.Model):
    """Cancellation record with refund tracking (SRS §2.2).

    Per SRS §2.2 cancellation rules:
      - 24+ hours before: full refund
      - 4+ hours before: 50% refund
      - <4 hours before: no refund
    """

    REFUND_CHOICES = [
        ("full", "Full refund (100%)"),
        ("half", "Half refund (50%)"),
        ("none", "No refund"),
    ]
    CANCELLATION_REASON_CHOICES = [
        ("counselee", "Cancelled by counselee"),
        ("counsellor", "Cancelled by counsellor"),
    ]

    session = models.OneToOneField(
        CounselingSession, on_delete=models.CASCADE, related_name="cancellation"
    )
    cancelled_by = models.CharField(
        _("cancelled by"), max_length=15, choices=CANCELLATION_REASON_CHOICES
    )
    reason = models.TextField(_("reason"), blank=True, default="")
    # Computed refund tier based on timing
    refund_tier = models.CharField(
        _("refund tier"), max_length=10, choices=REFUND_CHOICES, default="none"
    )
    refund_amount = models.DecimalField(
        _("refund amount"), max_digits=10, decimal_places=2, default=0
    )
    cancelled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("session cancellation")
        verbose_name_plural = _("session cancellations")

    def __str__(self) -> str:
        return f"Cancellation of Session #{self.session_id} ({self.refund_tier})"


class SessionSummary(models.Model):
    """Counsellor's post-session notes (SRS §3.3 + Doc 3).

    Per Doc 3 Session Summary form (6 fields):
    1. Client details and problem description (Text, mandatory)
    2. Session Summary (Text, mandatory)
    3. Provisional Diagnosis (Text, optional)
    4. Case Prognosis (Text, optional)
    5. Did the session go smoothly? (Yes/Somewhat/No + reason Text, mandatory)
    6. Is followup session needed? (Yes/No, mandatory)

    Per SRS §3.3: "Session Summary details available only to user and Admin."
    Filled by the counsellor after conducting the session.
    """

    session = models.OneToOneField(
        CounselingSession, on_delete=models.CASCADE, related_name="summary"
    )
    counsellor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="session_summaries",
    )
    # 1. Client details and problem description (mandatory)
    client_details = models.TextField(
        _("client details and problem description"),
        blank=True,
        default="",
        help_text=_("Client details and problem description (mandatory)"),
    )
    # 2. Session Summary (mandatory)
    summary = models.TextField(_("session summary"))
    # 3. Provisional Diagnosis (optional)
    provisional_diagnosis = models.TextField(_("provisional diagnosis"), blank=True, default="")
    # 4. Case Prognosis (optional)
    case_prognosis = models.TextField(_("case prognosis"), blank=True, default="")
    # 5. Did the session go smoothly?
    SMOOTHNESS_CHOICES = [
        ("yes", "Yes"),
        ("somewhat", "Somewhat"),
        ("no", "No"),
    ]
    session_smoothness = models.CharField(
        _("session smoothness"), max_length=10, choices=SMOOTHNESS_CHOICES, default="yes"
    )
    smoothness_reason = models.TextField(_("reason for smoothness rating"), blank=True, default="")
    # 6. Is followup session needed? (mandatory)
    followup_recommended = models.BooleanField(_("follow-up recommended"), default=False)
    # Legacy fields — kept for backward compatibility
    recommendations = models.TextField(_("recommendations"), blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("session summary")
        verbose_name_plural = _("session summaries")

    def __str__(self) -> str:
        return f"Summary for Session #{self.session_id}"


class SessionFeedback(models.Model):
    """Counselee's feedback after session (SRS §2.3 + Doc 3).

    Per Doc 3 feedback form (8 questions):
    1. Was the session useful? (Very useful / Useful / Somewhat / Not useful)
    2. How was it useful or not? (Text)
    3. Was the counsellor friendly and empathetic? (Very much / Somewhat / Not much)
    4. How did the session end? (On time / Before time / Late)
    5. Would you choose the counsellor again? (Yes / Maybe / No)
    6. Why would you or wouldn't you? (Text)
    7. How can we improve the service? (Text)
    8. Rate the Counsellor on a 10-point scale (10=excellent, 1=very poor)

    Per SRS §2.3: "User feedbacks are available only to Admin User."
    """

    session = models.OneToOneField(
        CounselingSession, on_delete=models.CASCADE, related_name="feedback"
    )
    counselee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="session_feedbacks",
    )
    # 1. Was the session useful?
    USEFULNESS_CHOICES = [
        ("very_useful", "Very useful"),
        ("useful", "Useful"),
        ("somewhat_useful", "Somewhat useful"),
        ("not_useful", "Not useful"),
    ]
    session_usefulness = models.CharField(
        _("session usefulness"), max_length=20, choices=USEFULNESS_CHOICES, default="useful"
    )
    # 2. How was it useful or not? (Text)
    usefulness_text = models.TextField(_("usefulness explanation"), blank=True, default="")
    # 3. Was the counsellor friendly and empathetic?
    EMPATHY_CHOICES = [
        ("very_much", "Very much"),
        ("somewhat", "Somewhat"),
        ("not_much", "Not much"),
    ]
    counsellor_empathy = models.CharField(
        _("counsellor empathy"), max_length=20, choices=EMPATHY_CHOICES, default="somewhat"
    )
    # 4. How did the session end?
    ENDING_CHOICES = [
        ("on_time", "Ended on time"),
        ("before_time", "Ended before time"),
        ("late", "Ended late"),
    ]
    session_ending = models.CharField(
        _("session ending"), max_length=20, choices=ENDING_CHOICES, default="on_time"
    )
    # 5. Would you choose the counsellor again?
    RECHOOSE_CHOICES = [
        ("yes", "Yes"),
        ("maybe", "May be"),
        ("no", "No"),
    ]
    would_rechoose = models.CharField(
        _("would rechoose counsellor"), max_length=10, choices=RECHOOSE_CHOICES, default="maybe"
    )
    # 6. Why would you or wouldn't you? (Text)
    rechoose_text = models.TextField(_("rechoose explanation"), blank=True, default="")
    # 7. How can we improve the service? (Text)
    improvement_suggestions = models.TextField(_("improvement suggestions"), blank=True, default="")
    # 8. Rate the Counsellor on a 10-point scale
    counsellor_rating = models.PositiveIntegerField(_("counsellor rating (1-10)"), default=5)
    # Legacy field — kept for backward compatibility
    rating = models.PositiveIntegerField(_("rating (1-5)"), default=3)
    experience_text = models.TextField(_("experience feedback"), blank=True, default="")
    counsellor_effectiveness = models.TextField(
        _("counsellor effectiveness"), blank=True, default=""
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("session feedback")
        verbose_name_plural = _("session feedbacks")

    def __str__(self) -> str:
        return f"Feedback for Session #{self.session_id} ({self.counsellor_rating}/10)"


class FollowupSession(models.Model):
    """A proposed follow-up session (SRS §3.3).

    Per SRS §3.3: when a counsellor recommends a follow-up, they specify
    a date/time. The counselee sees a countdown + initiates payment.
    """

    STATUS_CHOICES = [
        ("proposed", "Proposed (awaiting counselee payment)"),
        ("confirmed", "Confirmed (payment done)"),
        ("declined", "Declined by counselee"),
    ]

    original_session = models.ForeignKey(
        CounselingSession, on_delete=models.CASCADE, related_name="followups"
    )
    counsellor = models.ForeignKey(
        CounsellorProfile, on_delete=models.CASCADE, related_name="followup_sessions"
    )
    proposed_time = models.DateTimeField(_("proposed time"))
    status = models.CharField(
        _("status"), max_length=15, choices=STATUS_CHOICES, default="proposed"
    )
    # Link to the new session once confirmed (payment done)
    confirmed_session = models.OneToOneField(
        CounselingSession,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="parent_followup",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("follow-up session")
        verbose_name_plural = _("follow-up sessions")

    def __str__(self) -> str:
        return f"Followup for Session #{self.original_session_id} ({self.status})"


# ---------------------------------------------------------------------------
# CounselingSettings — singleton for terms, cancellation policy, etc.
# Per Doc 3 (Counselling review): CJ Admin defines terms & policies.
# ---------------------------------------------------------------------------


class CounselingSettings(models.Model):
    """Singleton model for counseling-wide settings.

    Stores terms & conditions, cancellation/refund policy, and other
    admin-defined text that is displayed to candidates during booking.
    Per Doc 3 Issues 1.9, 1.11.
    """

    terms_and_conditions = models.TextField(
        _("terms and conditions"),
        blank=True,
        default="",
        help_text=_("Terms & Conditions for counseling. Shown to candidate on booking."),
    )
    cancellation_policy = models.TextField(
        _("cancellation/refund policy"),
        blank=True,
        default="Before 24 hours: full refund. Before 4 hours: 50% refund. Less than 4 hours: no refund.",
        help_text=_("Cancellation and refund policy. Shown to candidate before cancellation."),
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("counseling settings")
        verbose_name_plural = _("counseling settings")

    def __str__(self) -> str:
        return "Counseling Settings"

    @classmethod
    def get(cls):
        """Get or create the singleton settings instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

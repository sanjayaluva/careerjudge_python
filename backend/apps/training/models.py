"""Models for the Training module.

Per SRS 07_training_setup_process.json:
  - Online-Standard training: media-based (video/audio/text) + assignments + assessments
  - Online-Live training: Zoom classrooms
  - Offline-Live training: real-time classroom sessions
  - Training Management: trainer modifies course contents (admin-gated)
  - Training Registration: end-user registers + pays + tracks progress

Models:
  - TrainingCategory: admin-created categories (e.g., 'IT', 'Soft Skills')
  - TrainingCourse: trainer-created course (scheduled/non-scheduled, duration, type)
  - CourseLesson: lessons within a course (ordered)
  - LessonTopic: subtopics under a lesson
  - TopicSession: sessions under a topic
  - SessionContent: video/audio/text content within a session
  - Assignment: additional materials + optional report submission
  - CourseAssessment: assessment link at session/topic/lesson/course level
  - LiveSession: scheduled online (Zoom) or offline classroom session
  - CourseCompletionParameter: which contents are mandatory for completion
  - CourseRegistration: end-user registration + payment + start time
  - CourseProgress: per-content progress tracking (completed, time-spent, last-accessed)
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TrainingCategory(models.Model):
    """Admin-created training category (e.g., 'IT', 'Soft Skills')."""

    name = models.CharField(_("name"), max_length=255, unique=True)
    description = models.TextField(_("description"), blank=True, default="")
    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = _("training category")
        verbose_name_plural = _("training categories")

    def __str__(self) -> str:
        return self.name


class TrainingCourse(models.Model):
    """A training course created by a trainer.

    Per SRS §2.1.1: trainer enters title, selects Scheduled/Non-Scheduled,
    and (if scheduled) specifies total duration allowed for completion.
    Per SRS §2 vs §3 vs §4: course type is online-standard, online-live,
    or offline-live.
    """

    COURSE_TYPE_CHOICES = [
        ("online_standard", "Online Standard (media-based)"),
        ("online_live", "Online Live (Zoom classroom)"),
        ("offline_live", "Offline Live (classroom)"),
    ]
    SCHEDULE_TYPE_CHOICES = [
        ("scheduled", "Scheduled (fixed duration)"),
        ("non_scheduled", "Non-Scheduled (self-paced)"),
    ]
    STATUS_CHOICES = [
        ("draft", "Draft (being configured)"),
        ("published", "Published (available for registration)"),
        ("archived", "Archived"),
    ]

    title = models.CharField(_("title"), max_length=255)
    objective = models.TextField(_("objective"), blank=True, default="")
    description = models.TextField(_("description"), blank=True, default="")
    image = models.TextField(
        _("image"), blank=True, default="", help_text=_("URL or base64 data URL of course image")
    )

    category = models.ForeignKey(
        TrainingCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses",
    )
    course_type = models.CharField(
        _("course type"), max_length=20, choices=COURSE_TYPE_CHOICES, default="online_standard"
    )
    schedule_type = models.CharField(
        _("schedule type"), max_length=20, choices=SCHEDULE_TYPE_CHOICES, default="non_scheduled"
    )
    # Total duration in days — only meaningful when schedule_type='scheduled'
    duration_days = models.PositiveIntegerField(
        _("duration (days)"),
        null=True,
        blank=True,
        help_text=_("Total duration allowed for course completion (scheduled courses only)"),
    )

    # Pricing — end-user pays to register
    price = models.DecimalField(
        _("price"), max_digits=10, decimal_places=2, default=0, help_text=_("Registration price")
    )

    status = models.CharField(_("status"), max_length=20, choices=STATUS_CHOICES, default="draft")

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_training_courses",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("training course")
        verbose_name_plural = _("training courses")

    def __str__(self) -> str:
        return self.title


class CourseLesson(models.Model):
    """A lesson within a course (SRS §2.2).

    Lessons are ordered and grouped into weeks (per SRS: 'System equally
    divides lessons across weeks and displays lesson list on a weekly basis').
    """

    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True, default="")
    order = models.PositiveIntegerField(_("order"), default=0)
    # Week number this lesson belongs to (1-based) — for the weekly grouping
    week_number = models.PositiveIntegerField(_("week number"), default=1)

    class Meta:
        ordering = ["week_number", "order"]
        verbose_name = _("course lesson")
        verbose_name_plural = _("course lessons")
        unique_together = [("course", "order")]

    def __str__(self) -> str:
        return f"{self.course.title} > {self.title}"


class LessonTopic(models.Model):
    """A subtopic under a lesson (SRS §2.2: 'any number of subtopics allowed')."""

    lesson = models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name="topics")
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True, default="")
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = _("lesson topic")
        verbose_name_plural = _("lesson topics")
        unique_together = [("lesson", "order")]

    def __str__(self) -> str:
        return f"{self.lesson.title} > {self.title}"


class TopicSession(models.Model):
    """A session under a topic (SRS §2.2: 'User adds sessions to each topic')."""

    topic = models.ForeignKey(LessonTopic, on_delete=models.CASCADE, related_name="sessions")
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True, default="")
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = _("topic session")
        verbose_name_plural = _("topic sessions")
        unique_together = [("topic", "order")]

    def __str__(self) -> str:
        return f"{self.topic.title} > {self.title}"


class SessionContent(models.Model):
    """Main session content — video/audio/text (SRS §2.3.1).

    For online-standard courses only. Online-live and offline-live courses
    use LiveSession instead.
    """

    CONTENT_FORMAT_CHOICES = [
        ("video", "Video"),
        ("audio", "Audio"),
        ("text", "Text"),
    ]

    session = models.ForeignKey(TopicSession, on_delete=models.CASCADE, related_name="contents")
    title = models.CharField(_("title"), max_length=255)
    content_format = models.CharField(
        _("content format"), max_length=10, choices=CONTENT_FORMAT_CHOICES, default="video"
    )
    # URL to the media file (video/audio) or text content
    # Stored as a URL or base64 data URL — same pattern as Question.image
    content_url = models.TextField(
        _("content URL"), blank=True, default="", help_text=_("URL or base64 data URL")
    )
    # Optional text content (for text format or transcript)
    text_content = models.TextField(_("text content"), blank=True, default="")
    duration_seconds = models.PositiveIntegerField(_("duration (seconds)"), null=True, blank=True)
    order = models.PositiveIntegerField(_("order"), default=0)
    # Per SRS §2.4.1.1 (Interlinking contents and assessments): contents
    # and assessments can be sequentially interlinked. This field controls
    # the playback sequence when interlinking is enabled. Null = use the
    # default 'order' field.
    sequence_order = models.PositiveIntegerField(
        _("sequence order"),
        null=True,
        blank=True,
        help_text=_(
            "Override order for interlinked playback (SRS §2.4.1.1). Null = use default order."
        ),
    )

    class Meta:
        ordering = ["order"]
        verbose_name = _("session content")
        verbose_name_plural = _("session contents")
        unique_together = [("session", "order")]

    def __str__(self) -> str:
        return f"{self.session.title} > {self.title} ({self.content_format})"


class Assignment(models.Model):
    """Additional training materials (SRS §2.3.2).

    Assignments are NOT part of the main session — they're additional
    study materials (videos, audios, docs, YouTube links, websites).
    Optionally enables report submission by students.
    """

    session = models.ForeignKey(TopicSession, on_delete=models.CASCADE, related_name="assignments")
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True, default="")
    # URL to external resource (YouTube, website, doc link, etc.)
    resource_url = models.URLField(_("resource URL"), blank=True, default="")
    # Whether students can submit a report for this assignment
    report_submission_enabled = models.BooleanField(_("report submission enabled"), default=False)
    report_instructions = models.TextField(_("report instructions"), blank=True, default="")
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = _("assignment")
        verbose_name_plural = _("assignments")

    def __str__(self) -> str:
        return f"{self.session.title} > {self.title}"


class CourseAssessment(models.Model):
    """Assessment attached at a specific level of the course (SRS §2.4).

    Links to an Assessment from the assessment module. The level field
    indicates where in the course the assessment sits:
      - during_session: within a specific session
      - end_of_session: at the end of a session
      - end_of_topic: at the end of a topic
      - end_of_lesson: at the end of a lesson
      - end_of_course: at the end of the entire course
    """

    ASSESSMENT_LEVEL_CHOICES = [
        ("during_session", "During Session"),
        ("end_of_session", "End of Session"),
        ("end_of_topic", "End of Topic"),
        ("end_of_lesson", "End of Lesson"),
        ("end_of_course", "End of Course"),
    ]

    course = models.ForeignKey(TrainingCourse, on_delete=models.CASCADE, related_name="assessments")
    assessment = models.ForeignKey(
        "assessment.Assessment",
        on_delete=models.CASCADE,
        related_name="training_course_assessments",
    )
    level = models.CharField(
        _("level"), max_length=20, choices=ASSESSMENT_LEVEL_CHOICES, default="end_of_session"
    )
    # Optional link to the specific session/topic/lesson this assessment
    # belongs to (required for during_session/end_of_session/end_of_topic/
    # end_of_lesson; null for end_of_course)
    session = models.ForeignKey(
        TopicSession, on_delete=models.CASCADE, null=True, blank=True, related_name="assessments"
    )
    title = models.CharField(_("title"), max_length=255)
    is_scored = models.BooleanField(_("is scored"), default=True)
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering = ["order"]
        verbose_name = _("course assessment")
        verbose_name_plural = _("course assessments")

    def __str__(self) -> str:
        return f"{self.course.title} > {self.title} ({self.level})"


class LiveSession(models.Model):
    """A scheduled live session — online (Zoom) or offline (classroom).

    Per SRS §2.5 + §3 + §4: live sessions are conducted periodically by
    the trainer. Online-live uses Zoom; offline-live is a real classroom.
    """

    SESSION_MODE_CHOICES = [
        ("online", "Online (Zoom)"),
        ("offline", "Offline (Classroom)"),
    ]
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    course = models.ForeignKey(
        TrainingCourse, on_delete=models.CASCADE, related_name="live_sessions"
    )
    title = models.CharField(_("title"), max_length=255)
    description = models.TextField(_("description"), blank=True, default="")
    mode = models.CharField(
        _("mode"), max_length=10, choices=SESSION_MODE_CHOICES, default="online"
    )
    # Zoom meeting URL (online mode) or physical venue address (offline mode)
    meeting_url = models.URLField(_("meeting URL"), blank=True, default="")
    venue = models.CharField(_("venue"), max_length=255, blank=True, default="")
    scheduled_at = models.DateTimeField(_("scheduled at"))
    duration_minutes = models.PositiveIntegerField(_("duration (minutes)"), default=60)
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["scheduled_at"]
        verbose_name = _("live session")
        verbose_name_plural = _("live sessions")

    def __str__(self) -> str:
        return f"{self.course.title} > {self.title} ({self.scheduled_at})"


class CourseCompletionParameter(models.Model):
    """Which contents are mandatory for course completion (SRS §2.6).

    Per SRS: trainer checks contents in each session/lesson/course to be
    mandatory for completion. Stored as a flag on each content type —
    but to keep it simple and flexible, we store explicit references
    here. A null content_type means the entire course must be completed.
    """

    CONTENT_TYPE_CHOICES = [
        ("session_content", "Session Content"),
        ("assignment", "Assignment"),
        ("assessment", "Assessment"),
        ("live_session", "Live Session"),
    ]

    course = models.ForeignKey(
        TrainingCourse, on_delete=models.CASCADE, related_name="completion_parameters"
    )
    content_type = models.CharField(_("content type"), max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id = models.PositiveIntegerField(_("content ID"))
    is_mandatory = models.BooleanField(_("is mandatory"), default=True)

    class Meta:
        verbose_name = _("course completion parameter")
        verbose_name_plural = _("course completion parameters")
        unique_together = [("course", "content_type", "content_id")]

    def __str__(self) -> str:
        return f"{self.course.title} > {self.content_type}#{self.content_id} (mandatory={self.is_mandatory})"


class CourseRegistration(models.Model):
    """End-user registration for a training course (SRS §6).

    Tracks the student, payment status, and (for scheduled courses) the
    start time from which the duration countdown begins.
    """

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Payment Pending"),
        ("paid", "Paid"),
        ("refunded", "Refunded"),
        ("failed", "Payment Failed"),
    ]
    COMPLETION_STATUS_CHOICES = [
        ("not_started", "Not Started"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("expired", "Expired (duration elapsed)"),
    ]

    course = models.ForeignKey(
        TrainingCourse, on_delete=models.CASCADE, related_name="registrations"
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="training_registrations"
    )
    payment_status = models.CharField(
        _("payment status"), max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )
    completion_status = models.CharField(
        _("completion status"),
        max_length=20,
        choices=COMPLETION_STATUS_CHOICES,
        default="not_started",
    )
    # For scheduled courses: the start time from which duration countdown begins
    started_at = models.DateTimeField(_("started at"), null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"), null=True, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registered_at"]
        verbose_name = _("course registration")
        verbose_name_plural = _("course registrations")
        unique_together = [("course", "student")]

    def __str__(self) -> str:
        return f"{self.student.email} -> {self.course.title} ({self.payment_status})"


class CourseProgress(models.Model):
    """Per-content progress tracking (SRS §6: 'Course Completion Status,
    Time Tracker, Option to resume from where last left').

    One row per (registration, content_type, content_id). Tracks whether
    the student completed the content, total time spent, and when they
    last accessed it.
    """

    CONTENT_TYPE_CHOICES = CourseCompletionParameter.CONTENT_TYPE_CHOICES

    registration = models.ForeignKey(
        CourseRegistration, on_delete=models.CASCADE, related_name="progress_records"
    )
    content_type = models.CharField(_("content type"), max_length=20, choices=CONTENT_TYPE_CHOICES)
    content_id = models.PositiveIntegerField(_("content ID"))
    is_completed = models.BooleanField(_("is completed"), default=False)
    time_spent_seconds = models.PositiveIntegerField(_("time spent (seconds)"), default=0)
    last_accessed_at = models.DateTimeField(_("last accessed at"), null=True, blank=True)

    class Meta:
        verbose_name = _("course progress")
        verbose_name_plural = _("course progress records")
        unique_together = [("registration", "content_type", "content_id")]

    def __str__(self) -> str:
        return (
            f"{self.registration.student.email} > {self.content_type}#{self.content_id} "
            f"({'done' if self.is_completed else 'in progress'})"
        )


class AssignmentReport(models.Model):
    """A student's report submission for an assignment (SRS §2.3.2).

    Per SRS §2.3.2 rule: "When end-user (student) submits the report, a
    notification is sent to the trainer. Trainer can open and view the
    report, give a score/rating, and enter feedback."

    Created when a student submits a report for an Assignment that has
    report_submission_enabled=True. The trainer then reviews it and
    fills in score + feedback.
    """

    STATUS_CHOICES = [
        ("submitted", "Submitted (awaiting trainer review)"),
        ("reviewed", "Reviewed by trainer"),
        ("resubmitted", "Resubmitted by student (after trainer feedback)"),
    ]

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name="reports")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignment_reports",
    )
    # The report content — either text or a file URL
    report_text = models.TextField(_("report text"), blank=True, default="")
    report_file_url = models.TextField(
        _("report file URL"),
        blank=True,
        default="",
        help_text=_("URL or base64 data URL of the uploaded report file"),
    )

    # Trainer review fields (filled when status moves to 'reviewed')
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="submitted"
    )
    trainer_score = models.FloatField(
        _("trainer score"), null=True, blank=True, help_text=_("Score given by trainer (0-100)")
    )
    trainer_feedback = models.TextField(_("trainer feedback"), blank=True, default="")
    reviewed_at = models.DateTimeField(_("reviewed at"), null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_assignment_reports",
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = _("assignment report")
        verbose_name_plural = _("assignment reports")
        unique_together = [("assignment", "student")]

    def __str__(self) -> str:
        return f"{self.student.email} > {self.assignment.title} ({self.status})"


class CourseMessage(models.Model):
    """A message between a student and trainer about a course (SRS §5).

    Per SRS §5 daily management tasks: "Check messages from end-users
    and respond." Messages are scoped to a CourseRegistration so they're
    tied to a specific student-course pair. Either the student or the
    trainer can send; the other party receives.
    """

    registration = models.ForeignKey(
        CourseRegistration, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_training_messages"
    )
    # The recipient is inferred from the registration + sender:
    #   - if sender is the student -> recipient is the course's trainer (created_by)
    #   - if sender is the trainer -> recipient is the student
    body = models.TextField(_("message body"))
    is_read = models.BooleanField(_("read by recipient"), default=False)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sent_at"]
        verbose_name = _("course message")
        verbose_name_plural = _("course messages")

    def __str__(self) -> str:
        return f"{self.sender.email} -> {self.registration.course.title} ({self.sent_at:%Y-%m-%d %H:%M})"


class LiveSessionConsent(models.Model):
    """Tracks whether a student has consented to attend a live session (SRS §5).

    Per SRS §5 scheduler_process note: "When student opens course page,
    a popup notification about upcoming event (Live Session) appears with
    meeting link. When student clicks 'Consent' button, notification goes
    back to trainer about student participation."

    This model records the student's consent/decline for each live session.
    The trainer can view the consent list to see who's attending.
    """

    STATUS_CHOICES = [
        ("consented", "Consented (will attend)"),
        ("declined", "Declined (will not attend)"),
    ]

    live_session = models.ForeignKey(LiveSession, on_delete=models.CASCADE, related_name="consents")
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="live_session_consents",
    )
    status = models.CharField(
        _("status"), max_length=10, choices=STATUS_CHOICES, default="consented"
    )
    consented_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-consented_at"]
        verbose_name = _("live session consent")
        verbose_name_plural = _("live session consents")
        unique_together = [("live_session", "student")]

    def __str__(self) -> str:
        return f"{self.student.email} -> {self.live_session.title} ({self.status})"


class InteractiveQuestion(models.Model):
    """A question embedded in a video/audio at a specific timestamp (SRS §2.3.1).

    Per SRS §2.3.1 Timeliner: the trainer sets a timeline marker for when
    a question should appear during video/audio playback. The student
    answers, and the system branches:
      - if correct  -> jump to correct_jump_to timestamp
      - if incorrect -> jump to incorrect_jump_to timestamp
    Then playback continues from the new position.

    The options field stores MCQ options as JSON:
      [{"id": 1, "text": "Option A", "is_correct": true}, ...]
    """

    session_content = models.ForeignKey(
        SessionContent, on_delete=models.CASCADE, related_name="interactive_questions"
    )
    question_text = models.TextField(_("question text"))
    # When in the media (seconds) this question should appear
    trigger_timestamp = models.FloatField(
        _("trigger timestamp (seconds)"),
        help_text=_("Seconds into the media when this question should appear"),
    )
    # MCQ options stored as JSON
    options = models.JSONField(
        _("options"),
        default=list,
        help_text=_('List of {"id": int, "text": str, "is_correct": bool} objects'),
    )
    # Branching: where to jump based on answer
    correct_jump_to = models.FloatField(
        _("correct answer jump-to (seconds)"),
        help_text=_("Timestamp to jump to if answered correctly"),
    )
    incorrect_jump_to = models.FloatField(
        _("incorrect answer jump-to (seconds)"),
        help_text=_("Timestamp to jump to if answered incorrectly"),
    )
    order = models.PositiveIntegerField(_("order"), default=0)

    class Meta:
        ordering = ["trigger_timestamp"]
        verbose_name = _("interactive question")
        verbose_name_plural = _("interactive questions")

    def __str__(self) -> str:
        return f"{self.session_content.title} @ {self.trigger_timestamp}s"

    @property
    def correct_option_id(self) -> int | None:
        """Return the ID of the correct option (first one with is_correct=True)."""
        for opt in self.options:
            if opt.get("is_correct"):
                return opt.get("id")
        return None

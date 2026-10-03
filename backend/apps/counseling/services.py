"""Counselling booking services (book / reschedule / cancel).

Shared by the counselee's own booking flow (``CounselingSessionViewSet``) and
the organization manager booking FOR a member (Report 9 #18/#19/#30/#31/#61,
``apps.organizations.views_licensing``), so slot availability, refunds and
notifications follow one set of rules.
"""

from django.db import transaction
from django.utils import timezone

from .models import CounselingSession, CounselingSettings, SessionCancellation, TimeSlot


class BookingError(Exception):
    """A booking/reschedule/cancel request that cannot be honoured."""


def _slot_str(timeslot) -> str:
    return timezone.localtime(timeslot.start_time).strftime("%Y-%m-%d %H:%M")


def _person(user) -> str:
    return user.full_name or user.email


def _claim_slot(timeslot_id, counsellor) -> TimeSlot:
    """Lock and return an open slot of ``counsellor``; raise if it is taken."""
    slot = TimeSlot.objects.select_for_update().get(id=timeslot_id)
    if slot.counsellor_id != counsellor.id:
        raise BookingError("This time slot belongs to another counsellor.")
    # A slot freed by a cancellation still carries that cancelled session
    # (one session per slot), so it cannot be booked again.
    if slot.status != "available" or CounselingSession.objects.filter(timeslot=slot).exists():
        raise BookingError("This time slot is no longer available.")
    return slot


def book_session(
    *,
    counselee,
    counsellor,
    timeslot,
    topic,
    category=None,
    description="",
    mode="online",
    organization=None,
    booked_by=None,
    request=None,
):
    """Book ``timeslot`` with ``counsellor`` for ``counselee``.

    Returns ``(session, checkout_url)``. When ``organization`` is given the
    session is booked by that organization's manager under its counselling
    licence (Report 9 #101): there is no fee for the member and no payment
    gateway step. Otherwise the counsellor's rate applies and, for a paid
    session, a Stripe Checkout URL is returned when the gateway is configured.
    """
    from apps.notifications.models import notify_role, notify_user
    from apps.payments.services import create_stripe_checkout_session, get_or_create_payment

    # Report 9 #105: a deactivated category is hidden from new bookings.
    if category is not None and not category.is_active:
        raise BookingError("This counselling category is not available.")
    with transaction.atomic():
        slot = _claim_slot(timeslot.id, counsellor)
        # Fee captured at booking time; licensed counselling costs the member
        # nothing (the organization's licence covers it).
        fee = 0 if organization is not None else counsellor.hourly_rate
        # H15/D8 §2.1: a session is only 'paid' once the gateway/webhook says
        # so — free sessions (fee=0) are the one exception.
        is_free = float(fee) == 0
        session = CounselingSession.objects.create(
            counselee=counselee,
            counsellor=counsellor,
            timeslot=slot,
            category=category,
            topic=topic,
            description=description or "",
            mode=mode or "online",
            fee=fee,
            status="pending",
            payment_status="paid" if is_free else "pending",
            terms_accepted=True,
            organization=organization,
            booked_by=booked_by,
        )
        slot.status = "booked"
        slot.save(update_fields=["status"])

    # Report 3 §1.10: notify the counsellor + helpdesk of the new booking.
    name = _person(counselee)
    when = _slot_str(slot)
    notify_user(
        counsellor.user,
        f"New booking: {name}",
        f"{name} booked a session for {when}. "
        f"Topic: {session.topic}. Please confirm within the confirm window.",
        "session",
        f"/counseling?session={session.id}",
    )
    notify_role(
        "helpdesk",
        f"New counselling booking: {name}",
        f"{name} booked a session with {counsellor.full_name} on {when}.",
        "session",
    )
    if organization is not None:
        # The member did not book it himself — tell him.
        notify_user(
            counselee,
            f"Counselling session booked: {counsellor.full_name}",
            f"{organization.name} booked a counselling session for you with "
            f"{counsellor.full_name} on {when}. Topic: {session.topic}.",
            "session",
            f"/counseling?session={session.id}",
        )

    # H15/D8 §2.1/§3.3: route payment through the gateway — same pattern as
    # training registration; the webhook flips payment_status to 'paid'.
    payment = get_or_create_payment(
        counselee,
        module="counseling",
        item_id=session.id,
        amount=fee,
        description=f"Counselling session with {counsellor.full_name}",
    )
    checkout_url = None
    if not is_free and request is not None:
        success_url = request.build_absolute_uri("/counseling?payment=success")
        cancel_url = request.build_absolute_uri("/counseling?payment=cancelled")
        checkout_url = create_stripe_checkout_session(payment, success_url, cancel_url)
    return session, checkout_url


def reschedule_session(session, new_timeslot):
    """Move a pending/confirmed session to another open slot of the same
    counsellor (Report 9 #19/#31/#61). The old slot is freed, the session goes
    back to 'pending' for the counsellor to confirm, and the counsellor,
    counselee and Help Desk are notified."""
    from apps.notifications.models import notify_role, notify_user

    if session.status not in ("pending", "confirmed"):
        raise BookingError(f"Cannot reschedule a session with status '{session.status}'.")
    if new_timeslot.start_time <= timezone.now():
        raise BookingError("Pick a time slot in the future.")
    with transaction.atomic():
        slot = _claim_slot(new_timeslot.id, session.counsellor)
        old = session.timeslot
        old_when = _slot_str(old)
        session.timeslot = slot
        session.status = "pending"
        session.confirmed_at = None
        session.save(update_fields=["timeslot", "status", "confirmed_at"])
        slot.status = "booked"
        slot.save(update_fields=["status"])
        old.status = "available"
        old.save(update_fields=["status"])

    name = _person(session.counselee)
    when = _slot_str(slot)
    notify_user(
        session.counsellor.user,
        f"Session rescheduled: {name}",
        f"{name}'s session on {old_when} has been moved to {when}. Please confirm it.",
        "session",
        f"/counseling?session={session.id}",
    )
    notify_user(
        session.counselee,
        f"Session rescheduled: {session.counsellor.full_name}",
        f"Your counselling session with {session.counsellor.full_name} has been moved "
        f"from {old_when} to {when}.",
        "session",
        f"/counseling?session={session.id}",
    )
    notify_role(
        "helpdesk",
        f"Session rescheduled: {session.counselee.email}",
        f"Session #{session.id} with {session.counsellor.full_name} moved from "
        f"{old_when} to {when}.",
        "session",
    )
    return session


def cancel_session(session, *, cancelled_by, reason):
    """Cancel a session with refund logic (SRS §2.2, Report 3 §1.15/§1.16).

    Refund rules (thresholds admin-configurable via CounselingSettings):
      - > full_refund_within_hours (default 24) before: full refund
      - > half_refund_within_hours (default 4) before: 50% refund
      - less: no refund

    Returns the ``SessionCancellation``. The counselee and Help Desk are
    notified by the cancellation signal.
    """
    if session.status in ("cancelled", "completed"):
        raise BookingError(f"Cannot cancel a session with status '{session.status}'.")
    if not (reason or "").strip():
        # Report 3 §1.16: reason is required for cancellations.
        raise BookingError("A reason is required to cancel.")

    settings = CounselingSettings.get()
    hours_until = (session.timeslot.start_time - timezone.now()).total_seconds() / 3600
    if hours_until >= settings.full_refund_within_hours:
        refund_tier, refund_amount = "full", session.fee
    elif hours_until >= settings.half_refund_within_hours:
        refund_tier, refund_amount = "half", session.fee / 2
    else:
        refund_tier, refund_amount = "none", 0

    # Dossier gap D8: execute the refund through the payments module rather
    # than only recording it here.
    refund_executed = False
    if refund_amount and float(refund_amount) > 0:
        from apps.payments.models import Payment
        from apps.payments.services import refund_payment

        payment = Payment.objects.filter(module="counseling", item_id=session.id).first()
        if payment:
            refund_executed = refund_payment(payment, amount=refund_amount)

    cancellation = SessionCancellation.objects.create(
        session=session,
        cancelled_by=cancelled_by,
        reason=reason,
        refund_tier=refund_tier,
        refund_amount=refund_amount,
        refund_executed=refund_executed,
    )
    session.status = "cancelled"
    session.payment_status = f"refunded_{refund_tier}"
    session.save(update_fields=["status", "payment_status"])

    # Free up the time. Code review: the slot itself stays with the cancelled
    # session (one session per slot, and deleting it would wipe the
    # cancellation/refund record), so it is marked 'cancelled' and a fresh
    # available slot is opened for the same time if that is still ahead.
    timeslot = session.timeslot
    timeslot.status = "cancelled"
    timeslot.save(update_fields=["status"])
    if timeslot.start_time > timezone.now():
        TimeSlot.objects.create(
            counsellor_id=timeslot.counsellor_id,
            start_time=timeslot.start_time,
            end_time=timeslot.end_time,
            status="available",
        )

    # Track counsellor cancellation frequency (SRS §3.2 note)
    if cancelled_by == "counsellor":
        profile = session.counsellor.user.profile
        profile.cancellation_count += 1
        profile.save(update_fields=["cancellation_count"])
    elif cancelled_by == "organization":
        # The counsellor loses the booking — tell him (the member and Help
        # Desk hear from the cancellation signal).
        from apps.notifications.models import notify_user

        notify_user(
            session.counsellor.user,
            f"Session cancelled: {_person(session.counselee)}",
            f"The session on {_slot_str(timeslot)} with {_person(session.counselee)} was "
            f"cancelled by their organization. Reason: {reason}",
            "warning",
            f"/counseling?session={session.id}",
        )
    return cancellation

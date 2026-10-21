"""Business rules for creating, validating, and rescheduling appointments."""

from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import Appointment, Doctor, Patient

SLOT_MINUTES = 30
MIN_NOTICE = timedelta(hours=1)


def validate_slot(
    doctor: Doctor,
    starts_at: datetime,
    *,
    exclude_appointment: Appointment | None = None,
) -> None:
    """Check that a proposed appointment conforms to booking rules.

    The start must be timezone-aware, at least one hour in the future, on the
    doctor's configured workday, within working hours, aligned to a half-hour
    boundary, and not already occupied by another booked appointment.

    Args:
        doctor: Doctor whose schedule and appointments govern the slot.
        starts_at: Proposed timezone-aware appointment start.
        exclude_appointment: Existing appointment to ignore while validating
            a reschedule, so its current slot does not conflict with itself.

    Raises:
        ValidationError: If the datetime is invalid or another active
            appointment already occupies the requested slot.
    """
    if timezone.is_naive(starts_at):
        raise ValidationError(
            {"starts_at": "Use an ISO-8601 datetime with a timezone offset."}
        )
    local_start = timezone.localtime(starts_at)
    local_end = local_start + timedelta(minutes=SLOT_MINUTES)
    if local_start < timezone.localtime(timezone.now()) + MIN_NOTICE:
        raise ValidationError(
            {"starts_at": "Appointments must be at least one hour in the future."}
        )
    if local_start.weekday() != doctor.working_day:
        raise ValidationError(
            {"starts_at": "The doctor does not work on this day."}
        )
    if (
        local_start.minute not in (0, 30)
        or local_start.second
        or local_start.microsecond
    ):
        raise ValidationError(
            {"starts_at": "Appointments must begin on a 30-minute boundary."}
        )
    if local_start.time() < doctor.start_time or local_end.time() > doctor.end_time:
        raise ValidationError(
            {
                "starts_at": (
                    "The requested slot is outside the doctor's working hours."
                )
            }
        )
    taken = Appointment.objects.filter(
        doctor=doctor,
        starts_at=starts_at,
        status="booked",
    )
    if exclude_appointment:
        taken = taken.exclude(pk=exclude_appointment.pk)
    if taken.exists():
        raise ValidationError({"starts_at": "This slot is already booked."})


@transaction.atomic
def create_appointment(
    *,
    doctor: Doctor,
    patient: Patient,
    starts_at: datetime,
) -> Appointment:
    """Validate and persist a new appointment in one transaction.

    The doctor row is locked while availability is checked and the new
    appointment is inserted. A database uniqueness violation caused by a
    concurrent booking is converted to a client-facing validation error.

    Args:
        doctor: Doctor requested for the appointment.
        patient: Patient who is booking the appointment.
        starts_at: Timezone-aware requested appointment start.

    Returns:
        The newly created appointment.

    Raises:
        ValidationError: If the slot fails business validation or is claimed
            concurrently by another request.
    """
    doctor = Doctor.objects.select_for_update().get(pk=doctor.pk)
    validate_slot(doctor, starts_at)
    try:
        return Appointment.objects.create(
            doctor=doctor,
            patient=patient,
            starts_at=starts_at,
        )
    except IntegrityError:
        raise ValidationError(
            {"starts_at": "This slot was just booked. Please choose another."}
        )


@transaction.atomic
def reschedule(appointment: Appointment, starts_at: datetime) -> Appointment:
    """Move a booked appointment after validating its replacement slot.

    The appointment's current slot is excluded from conflict detection while
    validating the new start. The write remains protected by the database
    constraint against concurrent bookings.

    Args:
        appointment: Existing appointment to move.
        starts_at: Timezone-aware replacement start time.

    Returns:
        The updated appointment.

    Raises:
        ValidationError: If the appointment is cancelled, the requested slot
            is invalid, or another request claims the slot concurrently.
    """
    if appointment.status == "cancelled":
        raise ValidationError(
            {"detail": "Cancelled appointments cannot be rescheduled."}
        )
    doctor = Doctor.objects.select_for_update().get(pk=appointment.doctor_id)
    validate_slot(doctor, starts_at, exclude_appointment=appointment)
    appointment.starts_at = starts_at
    try:
        appointment.save(update_fields=["starts_at", "updated_at"])
    except IntegrityError:
        raise ValidationError(
            {"starts_at": "This slot was just booked. Please choose another."}
        )
    return appointment

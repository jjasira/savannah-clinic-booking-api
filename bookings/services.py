from datetime import timedelta
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from .models import Appointment, Doctor

SLOT_MINUTES = 30
MIN_NOTICE = timedelta(hours=1)


def validate_slot(doctor: Doctor, starts_at, *, exclude_appointment=None):
    if timezone.is_naive(starts_at):
        raise ValidationError({"starts_at": "Use an ISO-8601 datetime with a timezone offset."})
    local_start = timezone.localtime(starts_at)
    local_end = local_start + timedelta(minutes=SLOT_MINUTES)
    if local_start < timezone.localtime(timezone.now()) + MIN_NOTICE:
        raise ValidationError({"starts_at": "Appointments must be at least one hour in the future."})
    if local_start.weekday() != doctor.working_day:
        raise ValidationError({"starts_at": "The doctor does not work on this day."})
    if local_start.minute not in (0, 30) or local_start.second or local_start.microsecond:
        raise ValidationError({"starts_at": "Appointments must begin on a 30-minute boundary."})
    if local_start.time() < doctor.start_time or local_end.time() > doctor.end_time:
        raise ValidationError({"starts_at": "The requested slot is outside the doctor's working hours."})
    taken = Appointment.objects.filter(doctor=doctor, starts_at=starts_at, status="booked")
    if exclude_appointment:
        taken = taken.exclude(pk=exclude_appointment.pk)
    if taken.exists():
        raise ValidationError({"starts_at": "This slot is already booked."})


@transaction.atomic
def create_appointment(*, doctor, patient, starts_at):
    doctor = Doctor.objects.select_for_update().get(pk=doctor.pk)
    validate_slot(doctor, starts_at)
    try:
        return Appointment.objects.create(doctor=doctor, patient=patient, starts_at=starts_at)
    except IntegrityError:
        raise ValidationError({"starts_at": "This slot was just booked. Please choose another."})


@transaction.atomic
def reschedule(appointment, starts_at):
    if appointment.status == "cancelled":
        raise ValidationError({"detail": "Cancelled appointments cannot be rescheduled."})
    doctor = Doctor.objects.select_for_update().get(pk=appointment.doctor_id)
    validate_slot(doctor, starts_at, exclude_appointment=appointment)
    appointment.starts_at = starts_at
    try:
        appointment.save(update_fields=["starts_at", "updated_at"])
    except IntegrityError:
        raise ValidationError({"starts_at": "This slot was just booked. Please choose another."})
    return appointment

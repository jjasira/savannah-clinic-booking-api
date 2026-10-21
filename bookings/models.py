from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models


class Doctor(models.Model):
    name = models.CharField(max_length=120)
    working_day = models.PositiveSmallIntegerField(
        help_text="Monday=0 through Sunday=6"
    )
    start_time = models.TimeField()
    end_time = models.TimeField()

    def clean(self) -> None:
        """Validate the doctor's configured working-hours interval.

        Django calls this during model validation. A valid schedule must end
        later on the same day than it starts; overnight shifts are not
        represented by this model.

        Raises:
            ValidationError: If the end time is not later than the start time.
        """
        if self.start_time >= self.end_time:
            raise DjangoValidationError(
                "Working-hours end time must be later than start time."
            )

    def __str__(self) -> str:
        """Return the doctor's name for admin and model representations."""
        return self.name


class Patient(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)

    def __str__(self) -> str:
        """Return the patient's full name for admin and model representations."""
        return self.full_name


class Appointment(models.Model):
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    starts_at = models.DateTimeField()
    status = models.CharField(
        max_length=10,
        choices=[("booked", "Booked"), ("cancelled", "Cancelled")],
        default="booked",
    )
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self) -> None:
        """Validate booked appointments against the doctor's schedule.

        Django admin model forms call ``full_clean`` before saving. Reusing the
        booking service here ensures appointments created or edited through
        admin follow the same timezone, schedule, notice, slot-boundary, and
        availability rules as API bookings. Cancelled records are exempt so
        historical appointments can still be managed.

        Raises:
            DjangoValidationError: If a booked appointment violates a booking
                rule.
        """
        super().clean()
        if (
            self.status != "booked"
            or self.doctor_id is None
            or self.starts_at is None
        ):
            return

        from rest_framework.exceptions import ValidationError as APIValidationError

        from .services import validate_slot

        try:
            validate_slot(
                self.doctor,
                self.starts_at,
                exclude_appointment=self if self.pk else None,
            )
        except APIValidationError as exc:
            if isinstance(exc.detail, dict):
                errors = {
                    field: [
                        str(message)
                        for message in (
                            messages if isinstance(messages, list) else [messages]
                        )
                    ]
                    for field, messages in exc.detail.items()
                }
                raise DjangoValidationError(errors) from exc
            raise DjangoValidationError(str(exc.detail)) from exc

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "starts_at"],
                condition=models.Q(status="booked"),
                name="one_active_booking_per_slot",
            )
        ]
        ordering = ["starts_at"]

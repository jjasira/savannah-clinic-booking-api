from django.core.exceptions import ValidationError
from django.db import models


class Doctor(models.Model):
    name = models.CharField(max_length=120)
    working_day = models.PositiveSmallIntegerField(help_text="Monday=0 through Sunday=6")
    start_time = models.TimeField()
    end_time = models.TimeField()

    def clean(self):
        if self.start_time >= self.end_time:
            raise ValidationError("Working-hours end time must be later than start time.")

    def __str__(self):
        return self.name


class Patient(models.Model):
    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.full_name


class Appointment(models.Model):
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="appointments")
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="appointments")
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=10, choices=[("booked", "Booked"), ("cancelled", "Cancelled")], default="booked")
    cancellation_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["doctor", "starts_at"], condition=models.Q(status="booked"), name="one_active_booking_per_slot")]
        ordering = ["starts_at"]

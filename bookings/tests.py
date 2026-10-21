"""Tests for appointment booking, cancellation, and rescheduling behavior."""

from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Appointment, Doctor, Patient


class BookingApiTests(TestCase):
    """Exercise the booking API using an isolated test database."""

    def setUp(self) -> None:
        """Create a patient, doctor, and valid future appointment slot.

        The slot is placed at 09:00 on the doctor's configured weekday. If
        today's 09:00 slot is too soon, the fixture advances by whole weeks
        until it satisfies the minimum booking notice.
        """
        self.client = APIClient()
        self.patient = Patient.objects.create(
            full_name="Amina Noor",
            email="amina@example.com",
        )
        today = timezone.localdate()
        self.doctor = Doctor.objects.create(
            name="Dr. Kamau",
            working_day=today.weekday(),
            start_time=time(8),
            end_time=time(17),
        )
        # Pick 09:00 on the next matching weekday that satisfies the
        # one-hour notice.
        candidate_day = today
        while True:
            candidate = timezone.make_aware(
                datetime.combine(candidate_day, time(9))
            )
            if candidate >= timezone.now() + timedelta(hours=1):
                self.slot = candidate
                break
            candidate_day += timedelta(days=7)

    def payload(
        self,
        slot: datetime | None = None,
    ) -> dict[str, int | str]:
        """Build the JSON payload for booking the fixture's doctor and patient.

        Args:
            slot: Optional appointment start to use instead of the fixture's
                default future slot.

        Returns:
            A request body containing doctor and patient IDs and an
            ISO-8601 timezone-aware start time.
        """
        return {
            "doctor": self.doctor.id,
            "patient": self.patient.id,
            "starts_at": (slot or self.slot).isoformat(),
        }

    def test_booking_and_double_booking_rejection(self) -> None:
        """Accept the first booking and reject another claim for that slot."""
        first = self.client.post("/appointments", self.payload(), format="json")
        second = self.client.post("/appointments", self.payload(), format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertIn("already booked", str(second.data))

    def test_cancellation_releases_slot(self) -> None:
        """Make a cancelled appointment's slot available for a new booking."""
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            starts_at=self.slot,
        )
        cancelled = self.client.patch(
            f"/appointments/{appointment.id}/cancel",
            {"reason": "No longer needed"},
            format="json",
        )
        rebooked = self.client.post("/appointments", self.payload(), format="json")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(rebooked.status_code, 201)

    def test_cancelled_cannot_be_rescheduled(self) -> None:
        """Reject attempts to move an appointment that is already cancelled."""
        appointment = Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            starts_at=self.slot,
            status="cancelled",
        )
        result = self.client.patch(
            f"/appointments/{appointment.id}/reschedule",
            {
                "starts_at": (
                    self.slot + timedelta(minutes=30)
                ).isoformat()
            },
            format="json",
        )
        self.assertEqual(result.status_code, 400)

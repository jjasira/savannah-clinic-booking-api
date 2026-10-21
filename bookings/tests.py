"""Tests for appointment booking, cancellation, and rescheduling behavior."""

from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.test import TestCase
from django.urls import reverse
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

    def future_midnight(self) -> datetime:
        """Return midnight on a future date matching the doctor's workday."""
        candidate_day = timezone.localdate()
        while candidate_day.weekday() != self.doctor.working_day:
            candidate_day += timedelta(days=1)

        midnight = timezone.make_aware(
            datetime.combine(candidate_day, time.min)
        )
        while midnight < timezone.now() + timedelta(hours=1):
            candidate_day += timedelta(days=7)
            midnight = timezone.make_aware(
                datetime.combine(candidate_day, time.min)
            )
        return midnight

    def past_working_slot(self) -> datetime:
        """Return 09:00 on the most recent past occurrence of the workday."""
        candidate_day = timezone.localdate() - timedelta(days=1)
        while candidate_day.weekday() != self.doctor.working_day:
            candidate_day -= timedelta(days=1)
        return timezone.make_aware(
            datetime.combine(candidate_day, time(9))
        )

    def test_booking_and_double_booking_rejection(self) -> None:
        """Accept the first booking and reject another claim for that slot."""
        first = self.client.post("/appointments", self.payload(), format="json")
        second = self.client.post("/appointments", self.payload(), format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertIn("already booked", str(second.data))

    def test_home_page_links_to_doctor_directory_and_api_guide(self) -> None:
        """Expose distinct doctor and API guide destinations from the home page."""
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("doctor-directory"))
        self.assertContains(response, reverse("api-guide"))

    def test_doctor_directory_shows_id_and_availability_url(self) -> None:
        """Show each doctor ID and a query link for the next workday."""
        response = self.client.get(reverse("doctor-directory"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Doctor ID: {self.doctor.pk}")
        self.assertContains(
            response,
            reverse(
                "availability",
                kwargs={"doctor_id": self.doctor.pk},
            ),
        )
        self.assertContains(response, "?date=")

    def test_booking_at_midnight_is_outside_doctor_hours(self) -> None:
        """Reject midnight bookings for a doctor working from 06:00 to 18:00."""
        self.doctor.start_time = time(6)
        self.doctor.end_time = time(18)
        self.doctor.save(update_fields=["start_time", "end_time"])

        response = self.client.post(
            "/appointments",
            self.payload(self.future_midnight()),
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("outside the doctor's working hours", str(response.data))

    def test_availability_returns_free_slots_and_excludes_booked_slots(self) -> None:
        """List future work-hour slots while omitting an active booking."""
        url = (
            f"/doctors/{self.doctor.pk}/availability"
            f"?date={self.slot.date().isoformat()}"
        )

        available_response = self.client.get(url)

        self.assertEqual(available_response.status_code, 200)
        available_slots = available_response.data["available_slots"]
        self.assertIn(self.slot.isoformat(), available_slots)
        self.assertTrue(
            all(
                datetime.fromisoformat(slot).minute in (0, 30)
                for slot in available_slots
            )
        )

        Appointment.objects.create(
            doctor=self.doctor,
            patient=self.patient,
            starts_at=self.slot,
        )
        booked_response = self.client.get(url)

        self.assertEqual(booked_response.status_code, 200)
        self.assertNotIn(
            self.slot.isoformat(),
            booked_response.data["available_slots"],
        )

    def test_model_validation_rejects_admin_booking_outside_hours(self) -> None:
        """Reject an out-of-hours booking during Django model-form validation."""
        self.doctor.start_time = time(6)
        self.doctor.end_time = time(18)
        self.doctor.save(update_fields=["start_time", "end_time"])
        appointment = Appointment(
            doctor=self.doctor,
            patient=self.patient,
            starts_at=self.future_midnight(),
        )

        with self.assertRaises(DjangoValidationError) as raised:
            appointment.full_clean()

        self.assertIn(
            "outside the doctor's working hours",
            str(raised.exception),
        )

    def test_admin_rejects_past_booked_appointment(self) -> None:
        """Prevent staff from saving a booked past appointment in Django admin."""
        admin_user = get_user_model().objects.create_superuser(
            username="clinic-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(admin_user)
        past_start = self.past_working_slot()

        response = self.client.post(
            "/admin/bookings/appointment/add/",
            {
                "doctor": self.doctor.pk,
                "patient": self.patient.pk,
                "starts_at_0": timezone.localtime(past_start).strftime(
                    "%Y-%m-%d"
                ),
                "starts_at_1": timezone.localtime(past_start).strftime(
                    "%H:%M:%S"
                ),
                "status": "booked",
                "cancellation_reason": "",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Appointments must be at least one hour in the future.",
        )
        self.assertFalse(
            Appointment.objects.filter(starts_at=past_start).exists()
        )

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

from datetime import datetime, timedelta, time
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from .models import Appointment, Doctor, Patient


class BookingApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.patient = Patient.objects.create(full_name="Amina Noor", email="amina@example.com")
        today = timezone.localdate()
        self.doctor = Doctor.objects.create(name="Dr. Kamau", working_day=today.weekday(), start_time=time(8), end_time=time(17))
        # Pick 09:00 on the next matching weekday that satisfies the one-hour notice.
        candidate_day = today
        while True:
            candidate = timezone.make_aware(datetime.combine(candidate_day, time(9)))
            if candidate >= timezone.now() + timedelta(hours=1):
                self.slot = candidate
                break
            candidate_day += timedelta(days=7)

    def payload(self, slot=None):
        return {"doctor": self.doctor.id, "patient": self.patient.id, "starts_at": (slot or self.slot).isoformat()}

    def test_booking_and_double_booking_rejection(self):
        first = self.client.post("/appointments", self.payload(), format="json")
        second = self.client.post("/appointments", self.payload(), format="json")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 400)
        self.assertIn("already booked", str(second.data))

    def test_cancellation_releases_slot(self):
        appointment = Appointment.objects.create(doctor=self.doctor, patient=self.patient, starts_at=self.slot)
        cancelled = self.client.patch(f"/appointments/{appointment.id}/cancel", {"reason": "No longer needed"}, format="json")
        rebooked = self.client.post("/appointments", self.payload(), format="json")
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(rebooked.status_code, 201)

    def test_cancelled_cannot_be_rescheduled(self):
        appointment = Appointment.objects.create(doctor=self.doctor, patient=self.patient, starts_at=self.slot, status="cancelled")
        result = self.client.patch(f"/appointments/{appointment.id}/reschedule", {"starts_at": (self.slot + timedelta(minutes=30)).isoformat()}, format="json")
        self.assertEqual(result.status_code, 400)

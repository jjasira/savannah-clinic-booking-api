"""HTTP views for the clinic pages and appointment API."""

from datetime import datetime, timedelta

from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Appointment, Doctor, Patient
from .serializers import (
    AppointmentSerializer,
    CancelSerializer,
    RescheduleSerializer,
)
from .services import reschedule


def home(request: HttpRequest) -> HttpResponse:
    """Render the public landing page.

    Args:
        request: Incoming Django HTTP request.

    Returns:
        The rendered clinic home page.
    """
    return render(request, "bookings/home.html")


def api_guide(request: HttpRequest) -> HttpResponse:
    """Render the browser-based API reference page.

    Args:
        request: Incoming Django HTTP request.

    Returns:
        The rendered API guide page.
    """
    return render(request, "bookings/api_guide.html")


@api_view(["POST"])
def appointment_create(request: Request) -> Response:
    """Validate and create a new appointment from a JSON request.

    Args:
        request: DRF request containing doctor, patient, and start-time data.

    Returns:
        HTTP 201 with the serialized appointment when booking succeeds.

    Raises:
        ValidationError: If the request data or requested slot is invalid.
    """
    serializer = AppointmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    appointment = serializer.save()
    return Response(
        AppointmentSerializer(appointment).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def availability(request: Request, doctor_id: int) -> Response:
    """Return available half-hour slots for a doctor on a requested date.

    Args:
        request: DRF request with the required ``date=YYYY-MM-DD`` query
            parameter.
        doctor_id: Primary key of the doctor whose availability is requested.

    Returns:
        A JSON response containing the doctor, date, and available start
        times. A non-working weekday produces an empty slot list.

    Raises:
        Http404: If the doctor does not exist.
        ValidationError: If the date query parameter is missing or malformed.
    """
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    raw_date = request.query_params.get("date")
    if not raw_date:
        raise ValidationError(
            {"date": "This query parameter is required (YYYY-MM-DD)."}
        )
    try:
        day = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({"date": "Use YYYY-MM-DD."})
    if day.weekday() != doctor.working_day:
        return Response(
            {"doctor": doctor.id, "date": raw_date, "available_slots": []}
        )
    tz = timezone.get_current_timezone()
    current = timezone.make_aware(
        datetime.combine(day, doctor.start_time),
        tz,
    )
    finish = timezone.make_aware(
        datetime.combine(day, doctor.end_time),
        tz,
    )
    occupied = set(
        Appointment.objects.filter(
            doctor=doctor,
            status="booked",
            starts_at__gte=current,
            starts_at__lt=finish,
        ).values_list("starts_at", flat=True)
    )
    now = timezone.now() + timedelta(hours=1)
    slots = []
    while current + timedelta(minutes=30) <= finish:
        if current not in occupied and current >= now:
            slots.append(current.isoformat())
        current += timedelta(minutes=30)
    return Response(
        {"doctor": doctor.id, "date": raw_date, "available_slots": slots}
    )


@api_view(["PATCH"])
def cancel(request: Request, appointment_id: int) -> Response:
    """Cancel an appointment and release its time slot.

    The appointment is locked while checking its current status and saving the
    cancellation reason, preventing concurrent cancellation updates.

    Args:
        request: DRF request containing a non-empty cancellation reason.
        appointment_id: Primary key of the appointment to cancel.

    Returns:
        The updated appointment, or HTTP 409 if it is already cancelled.

    Raises:
        Http404: If the appointment does not exist.
        ValidationError: If the cancellation reason is invalid.
    """
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    data = CancelSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(
            pk=appointment.pk
        )
        if appointment.status == "cancelled":
            return Response(
                {"detail": "Appointment is already cancelled."},
                status=status.HTTP_409_CONFLICT,
            )
        appointment.status, appointment.cancellation_reason = (
            "cancelled",
            data.validated_data["reason"],
        )
        appointment.save(
            update_fields=["status", "cancellation_reason", "updated_at"]
        )
    return Response(AppointmentSerializer(appointment).data)


@api_view(["PATCH"])
def appointment_reschedule(request: Request, appointment_id: int) -> Response:
    """Validate and move an appointment to a new start time.

    Args:
        request: DRF request containing the timezone-aware replacement start.
        appointment_id: Primary key of the appointment to reschedule.

    Returns:
        The updated appointment representation.

    Raises:
        Http404: If the appointment does not exist.
        ValidationError: If the new start is invalid or the appointment is
            cancelled.
    """
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    data = RescheduleSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    appointment = reschedule(appointment, data.validated_data["starts_at"])
    return Response(AppointmentSerializer(appointment).data)


@api_view(["GET"])
def patient_appointments(request: Request, patient_id: int) -> Response:
    """List a patient's future booked appointments in start-time order.

    Args:
        request: DRF request for the patient appointment listing.
        patient_id: Primary key of the patient whose appointments are listed.

    Returns:
        A JSON array of upcoming booked appointments.

    Raises:
        Http404: If the patient does not exist.
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    appointments = patient.appointments.filter(
        status="booked",
        starts_at__gte=timezone.now(),
    )
    return Response(AppointmentSerializer(appointments, many=True).data)

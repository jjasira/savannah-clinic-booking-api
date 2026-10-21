from datetime import datetime, timedelta
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .models import Appointment, Doctor, Patient
from .serializers import AppointmentSerializer, CancelSerializer, RescheduleSerializer
from .services import reschedule


def home(request):
    return render(request, "bookings/home.html")


def api_guide(request):
    return render(request, "bookings/api_guide.html")


@api_view(["POST"])
def appointment_create(request):
    serializer = AppointmentSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    appointment = serializer.save()
    return Response(AppointmentSerializer(appointment).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def availability(request, doctor_id):
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    raw_date = request.query_params.get("date")
    if not raw_date:
        raise ValidationError({"date": "This query parameter is required (YYYY-MM-DD)."})
    try:
        day = datetime.strptime(raw_date, "%Y-%m-%d").date()
    except ValueError:
        raise ValidationError({"date": "Use YYYY-MM-DD."})
    if day.weekday() != doctor.working_day:
        return Response({"doctor": doctor.id, "date": raw_date, "available_slots": []})
    tz = timezone.get_current_timezone()
    current = timezone.make_aware(datetime.combine(day, doctor.start_time), tz)
    finish = timezone.make_aware(datetime.combine(day, doctor.end_time), tz)
    occupied = set(Appointment.objects.filter(doctor=doctor, status="booked", starts_at__gte=current, starts_at__lt=finish).values_list("starts_at", flat=True))
    now = timezone.now() + timedelta(hours=1)
    slots = []
    while current + timedelta(minutes=30) <= finish:
        if current not in occupied and current >= now:
            slots.append(current.isoformat())
        current += timedelta(minutes=30)
    return Response({"doctor": doctor.id, "date": raw_date, "available_slots": slots})


@api_view(["PATCH"])
def cancel(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    data = CancelSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    with transaction.atomic():
        appointment = Appointment.objects.select_for_update().get(pk=appointment.pk)
        if appointment.status == "cancelled":
            return Response({"detail": "Appointment is already cancelled."}, status=status.HTTP_409_CONFLICT)
        appointment.status, appointment.cancellation_reason = "cancelled", data.validated_data["reason"]
        appointment.save(update_fields=["status", "cancellation_reason", "updated_at"])
    return Response(AppointmentSerializer(appointment).data)


@api_view(["PATCH"])
def appointment_reschedule(request, appointment_id):
    appointment = get_object_or_404(Appointment, pk=appointment_id)
    data = RescheduleSerializer(data=request.data)
    data.is_valid(raise_exception=True)
    appointment = reschedule(appointment, data.validated_data["starts_at"])
    return Response(AppointmentSerializer(appointment).data)


@api_view(["GET"])
def patient_appointments(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    appointments = patient.appointments.filter(status="booked", starts_at__gte=timezone.now())
    return Response(AppointmentSerializer(appointments, many=True).data)

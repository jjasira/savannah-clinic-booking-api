from typing import Any

from rest_framework import serializers

from .models import Appointment
from .services import create_appointment


class AppointmentSerializer(serializers.ModelSerializer):
    """Serialize appointment data and delegate validated creation to services."""

    class Meta:
        model = Appointment
        fields = [
            "id",
            "doctor",
            "patient",
            "starts_at",
            "status",
            "cancellation_reason",
            "created_at",
        ]
        read_only_fields = ["id", "status", "cancellation_reason", "created_at"]

    def create(self, validated_data: dict[str, Any]) -> Appointment:
        """Create an appointment through the booking-rule service.

        Args:
            validated_data: Serializer-validated model values, including the
                doctor, patient, and timezone-aware appointment start time.

        Returns:
            The newly persisted appointment.
        """
        return create_appointment(**validated_data)


class CancelSerializer(serializers.Serializer):
    """Validate the reason supplied when cancelling an appointment."""

    reason = serializers.CharField(min_length=1, max_length=1000)


class RescheduleSerializer(serializers.Serializer):
    """Validate the new start time supplied for rescheduling."""

    starts_at = serializers.DateTimeField()


class SlotSerializer(serializers.Serializer):
    """Represent a single appointment start time."""

    starts_at = serializers.DateTimeField()

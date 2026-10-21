from rest_framework import serializers
from .models import Appointment, Doctor, Patient
from .services import create_appointment


class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = ["id", "doctor", "patient", "starts_at", "status", "cancellation_reason", "created_at"]
        read_only_fields = ["id", "status", "cancellation_reason", "created_at"]

    def create(self, validated_data):
        return create_appointment(**validated_data)


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=1, max_length=1000)


class RescheduleSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()


class SlotSerializer(serializers.Serializer):
    starts_at = serializers.DateTimeField()

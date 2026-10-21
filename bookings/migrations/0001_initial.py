# Generated manually for this assessment.
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(name="Doctor", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=120)), ("working_day", models.PositiveSmallIntegerField(help_text="Monday=0 through Sunday=6")), ("start_time", models.TimeField()), ("end_time", models.TimeField())]),
        migrations.CreateModel(name="Patient", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("full_name", models.CharField(max_length=120)), ("email", models.EmailField(max_length=254, unique=True))]),
        migrations.CreateModel(name="Appointment", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("starts_at", models.DateTimeField()), ("status", models.CharField(choices=[("booked", "Booked"), ("cancelled", "Cancelled")], default="booked", max_length=10)), ("cancellation_reason", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)), ("doctor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="bookings.doctor")), ("patient", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="bookings.patient"))]),
        migrations.AddConstraint(model_name="appointment", constraint=models.UniqueConstraint(condition=models.Q(("status", "booked")), fields=("doctor", "starts_at"), name="one_active_booking_per_slot")),
    ]

from django.urls import URLPattern, path

from . import views

urlpatterns: list[URLPattern] = [
    path("", views.home, name="home"),
    path("doctors/", views.doctor_directory, name="doctor-directory"),
    path("docs/", views.api_guide, name="api-guide"),
    path("appointments", views.appointment_create, name="appointment-create"),
    path(
        "appointments/<int:appointment_id>/cancel",
        views.cancel,
        name="appointment-cancel",
    ),
    path(
        "appointments/<int:appointment_id>/reschedule",
        views.appointment_reschedule,
        name="appointment-reschedule",
    ),
    path(
        "doctors/<int:doctor_id>/availability",
        views.availability,
        name="availability",
    ),
    path(
        "patients/<int:patient_id>/appointments",
        views.patient_appointments,
        name="patient-appointments",
    ),
]

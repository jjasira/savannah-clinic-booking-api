from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("docs/", views.api_guide, name="api-guide"),
    path("appointments", views.appointment_create),
    path("appointments/<int:appointment_id>/cancel", views.cancel),
    path("appointments/<int:appointment_id>/reschedule", views.appointment_reschedule),
    path("doctors/<int:doctor_id>/availability", views.availability),
    path("patients/<int:patient_id>/appointments", views.patient_appointments),
]

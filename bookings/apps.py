from django.apps import AppConfig


class BookingsConfig(AppConfig):
    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "bookings"

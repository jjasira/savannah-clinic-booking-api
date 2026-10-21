"""Django settings for local development and the Render deployment."""

import os
from pathlib import Path

import dj_database_url

BASE_DIR: Path = Path(__file__).resolve().parent.parent
SECRET_KEY: str = os.getenv("DJANGO_SECRET_KEY", "unsafe-development-key")
DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"
ALLOWED_HOSTS: list[str] = [
    host for host in os.getenv("ALLOWED_HOSTS", "*").split(",") if host
]

INSTALLED_APPS: list[str] = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "bookings",
]
MIDDLEWARE: list[str] = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
ROOT_URLCONF: str = "clinic_project.urls"
TEMPLATES: list[dict[str, object]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION: str = "clinic_project.wsgi.application"
DATABASES: dict[str, dict[str, object]] = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}
LANGUAGE_CODE: str = "en-us"
TIME_ZONE: str = os.getenv("TIME_ZONE", "Africa/Nairobi")
USE_I18N: bool = True
USE_TZ: bool = True
STATIC_URL: str = "static/"
STATIC_ROOT: Path = BASE_DIR / "staticfiles"
STATICFILES_STORAGE: str = "whitenoise.storage.CompressedManifestStaticFilesStorage"
DEFAULT_AUTO_FIELD: str = "django.db.models.BigAutoField"
REST_FRAMEWORK: dict[str, list[str]] = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
}

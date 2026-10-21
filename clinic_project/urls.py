from django.contrib import admin
from django.urls import include, path
from django.urls.resolvers import URLPattern, URLResolver

urlpatterns: list[URLPattern | URLResolver] = [
    path("admin/", admin.site.urls),
    path("", include("bookings.urls")),
]

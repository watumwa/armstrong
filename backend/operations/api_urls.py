from django.urls import path

from . import api


urlpatterns = [
    path("health", api.health),
    path("auth/login", api.login),
    path("auth/logout", api.logout),
    path("auth/me", api.me),
    path("auth/change-password", api.change_password),
    path("facilities", api.facilities),
    path("facilities/<uuid:facility_id>", api.facility_detail),
    path("users", api.users),
    path("collections", api.collections),
    path("payments", api.payments),
    path("reports/summary", api.report_summary),
]

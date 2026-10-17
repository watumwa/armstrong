from django.urls import path

from . import api, fleet_api, fleet_gps, fleet_verification, fleet_reports, fleet_sync, fleet_alerts, fleet_receipts


urlpatterns = [
    path('fleet/alerts', fleet_alerts.list_alerts),
    path('fleet/alerts/scan', fleet_alerts.scan_alerts),
    path('fleet/alerts/<uuid:alert_id>/resolve', fleet_alerts.resolve_alert),
    path('fleet/receipts/<uuid:verification_id>', fleet_receipts.receipt),
    path('fleet/sync', fleet_sync.sync_events),
    path('fleet/reports/summary', fleet_reports.fleet_summary),
    path('fleet/facilities/<uuid:facility_id>/qr', fleet_verification.facility_qr),
    path('fleet/stops/<uuid:stop_id>/verify', fleet_verification.verify_stop),
    path('fleet/trips/<uuid:trip_id>/location', fleet_gps.report_location),
    path('fleet/trips/<uuid:trip_id>/history', fleet_gps.trip_history),
    path('fleet/locations/latest', fleet_gps.latest_locations),
    path('fleet/vehicles', fleet_api.vehicles),
    path('fleet/drivers', fleet_api.drivers),
    path('fleet/assignments', fleet_api.assignments),
    path('fleet/assignments/<uuid:assignment_id>/end', fleet_api.end_assignment),
    path('fleet/trips', fleet_api.trips),
    path('fleet/trips/<uuid:trip_id>/<str:operation>', fleet_api.trip_action),
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

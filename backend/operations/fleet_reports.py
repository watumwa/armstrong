"""Fleet performance dashboard: read-only aggregation with bounded data."""
from django.db.models import Count
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .fleet_models import Vehicle, FleetTrip, TripStop, StopVerification, LocationPing
from .views import check_role

@api_view(["GET"])
def fleet_summary(request):
    check_role(request.user,"Administrator","Supervisor")
    return Response({
        "vehicles": Vehicle.objects.count(),
        "available_vehicles": Vehicle.objects.filter(status="available").count(),
        "trips_by_status": {row["status"]:row["count"] for row in FleetTrip.objects.values("status").annotate(count=Count("id"))},
        "stops_by_status": {row["status"]:row["count"] for row in TripStop.objects.values("status").annotate(count=Count("id"))},
        "verified_stops": StopVerification.objects.count(),
        "gps_reports": LocationPing.objects.count(),
        "note": "Totals are cumulative, not date-filtered."
    })

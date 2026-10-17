"""Fleet alerts: stale active-trip GPS, overdue planned trips, and resolution."""
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .fleet_models import FleetAlert, FleetTrip, LocationPing
from .views import check_role, log

@api_view(["GET"])
def list_alerts(request):
    check_role(request.user,"Administrator","Supervisor")
    qs=FleetAlert.objects.order_by("-created_at")
    if request.query_params.get("unresolved")=="true":qs=qs.filter(resolved_at__isnull=True)
    return Response({"alerts":[{"id":str(a.id),"severity":a.severity,"category":a.category,"message":a.message,
        "trip_id":str(a.trip_id) if a.trip_id else None,"created_at":a.created_at.isoformat(),
        "resolved_at":a.resolved_at.isoformat() if a.resolved_at else None} for a in qs[:100]]})

def detect_alerts(now=None):
    """Idempotent fleet exception scan, callable by a scheduled command."""
    now=now or timezone.now()
    new=0
    for trip in FleetTrip.objects.select_related("vehicle").filter(status__in=["active","planned"]).order_by("id").iterator(chunk_size=200):
        category=None
        if trip.status=="planned" and trip.scheduled_for<now-timedelta(hours=2):
            category="overdue_departure"
        elif trip.status=="active":
            latest=LocationPing.objects.filter(trip=trip).order_by("-received_at").values_list("received_at",flat=True).first()
            if not latest or latest<now-timedelta(minutes=15):
                category="stale_gps"
        if category:
            key=f"{category}:{trip.id}"
            _,created=FleetAlert.objects.get_or_create(alert_key=key,defaults={
                "trip":trip,"severity":"warning","category":category,
                "message":f"Trip {trip.id} ({trip.vehicle.registration}) requires attention: {category.replace('_',' ')}"})
            if created:new+=1
    return new

@api_view(["POST"])
def scan_alerts(request):
    check_role(request.user,"Administrator","Supervisor")
    return Response({"created":detect_alerts(),"note":"All planned and active trips scanned; duplicate alerts are suppressed."})

@api_view(["POST"])
def resolve_alert(request,alert_id):
    check_role(request.user,"Administrator","Supervisor")
    with transaction.atomic():
        alert=FleetAlert.objects.select_for_update().filter(pk=alert_id).first()
        if not alert:return Response({"error":"Alert not found"},status=404)
        if alert.resolved_at is None:
            alert.resolved_at=timezone.now()
            alert.save(update_fields=["resolved_at"])
            log(request.user,"fleet.alert.resolved",alert)
    return Response({"ok":True})

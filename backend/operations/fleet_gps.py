"""Phase 2 GPS endpoints: drivers opt in during active work trips."""
import math
import uuid
from datetime import timedelta
from django.db import IntegrityError
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .fleet_models import FleetTrip, LocationPing
from .views import check_role

def serialize(p):
    return {"latitude":p.latitude,"longitude":p.longitude,"accuracy_m":p.accuracy_m,
            "captured_at":p.captured_at.isoformat(),"received_at":p.received_at.isoformat(),
            "trip_id":str(p.trip_id)}

@api_view(["POST"])
def report_location(request, trip_id):
    check_role(request.user, "Waste Collector")
    trip=FleetTrip.objects.filter(pk=trip_id,driver=request.user,status="active").first()
    if not trip:
        return Response({"error":"Active assigned trip required"},status=403)
    try:
        lat=float(request.data.get("latitude"))
        lon=float(request.data.get("longitude"))
        accuracy=float(request.data.get("accuracy_m"))
        event_id=uuid.UUID(str(request.data.get("client_event_id")))
        captured=parse_datetime(str(request.data.get("captured_at","")))
    except (TypeError,ValueError,OverflowError):
        return Response({"error":"Invalid location payload"},status=400)
    if not captured or timezone.is_naive(captured) or not all(map(math.isfinite,[lat,lon,accuracy])):
        return Response({"error":"Valid timezone-aware location required"},status=400)
    if not (-90<=lat<=90 and -180<=lon<=180 and 0<=accuracy<=1000):
        return Response({"error":"Location coordinates or accuracy out of range"},status=400)
    now=timezone.now()
    if captured>now+timedelta(minutes=5) or captured<now-timedelta(hours=24) or captured<trip.started_at-timedelta(minutes=5):
        return Response({"error":"Location timestamp outside active trip window"},status=400)
    try:
        ping,created=LocationPing.objects.get_or_create(client_event_id=event_id,defaults={
            "trip":trip,"driver":request.user,"latitude":lat,"longitude":lon,
            "accuracy_m":accuracy,"captured_at":captured})
    except IntegrityError:
        ping=LocationPing.objects.get(client_event_id=event_id)
        created=False
    if ping.trip_id!=trip.id or ping.driver_id!=request.user.id:
        return Response({"error":"Location event ID already used"},status=409)
    return Response({"ok":True,"duplicate":not created},status=201 if created else 200)

@api_view(["GET"])
def latest_locations(request):
    check_role(request.user,"Administrator","Supervisor")
    active=FleetTrip.objects.filter(status="active").select_related("vehicle","driver").order_by("-started_at")[:100]
    result=[]
    now=timezone.now()
    for trip in active:
        ping=LocationPing.objects.filter(trip=trip).order_by("-captured_at").first()
        result.append({"trip_id":str(trip.id),"registration":trip.vehicle.registration,
                       "driver_name":trip.driver.name,"last_location":serialize(ping) if ping else None,
                       "fresh":bool(ping and (now-ping.received_at).total_seconds()<=120)})
    return Response({"vehicles":result,"note":"Fresh means received within 120 seconds; it is not continuous live tracking."})

@api_view(["GET"])
def trip_history(request,trip_id):
    trip=FleetTrip.objects.filter(pk=trip_id).first()
    if not trip:return Response({"error":"Trip not found"},status=404)
    if request.user.role not in ("Administrator","Supervisor") and request.user.pk!=trip.driver_id:
        raise PermissionDenied("Not authorized for this trip")
    pings=LocationPing.objects.filter(trip=trip).order_by("-captured_at")[:500]
    return Response({"trip_id":str(trip.id),"locations":[serialize(p) for p in reversed(list(pings))]})

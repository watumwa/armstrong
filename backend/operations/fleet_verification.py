"""Trip stop geofence and QR checks. QR tokens are signed, not facility IDs."""
import math
import uuid
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .fleet_models import FleetTrip, TripStop, StopVerification
from .views import check_role, log

RADIUS_METRES = 150

def distance_m(a,b,c,d):
    r=6371000
    x1,x2=math.radians(a),math.radians(c)
    dx=x2-x1
    dy=math.radians(d-b)
    h=math.sin(dx/2)**2+math.cos(x1)*math.cos(x2)*math.sin(dy/2)**2
    return 2*r*math.asin(min(1,math.sqrt(h)))

@api_view(["GET"])
def facility_qr(request, facility_id):
    check_role(request.user,"Administrator","Supervisor")
    from .models import Facility
    facility=Facility.objects.filter(pk=facility_id).first()
    if not facility:return Response({"error":"Facility not found"},status=404)
    token=signing.dumps({"facility_id":str(facility.id)},salt="armstrong-facility-qr-v1")
    return Response({"facility_id":str(facility.id),"facility_name":facility.name,"qr_token":token,
                     "note":"Print this signed QR code at the facility. Do not treat it as proof of physical presence."})

@api_view(["POST"])
def verify_stop(request,stop_id):
    return process_verification(request,stop_id)

def process_verification(request,stop_id):
    check_role(request.user,"Waste Collector")
    stop=TripStop.objects.select_related("trip","facility").filter(pk=stop_id,trip__driver=request.user,trip__status="active").first()
    if not stop:return Response({"error":"Active assigned trip stop required"},status=403)
    try:
        event=uuid.UUID(str(request.data.get("event_id")))
        lat=float(request.data.get("latitude"))
        lon=float(request.data.get("longitude"))
        accuracy=float(request.data.get("accuracy_m"))
    except (ValueError,TypeError,OverflowError):
        return Response({"error":"Valid GPS coordinates, accuracy and event ID required"},status=400)
    if not all(map(math.isfinite,[lat,lon,accuracy])) or not (-90<=lat<=90 and -180<=lon<=180 and 0<=accuracy<=1000):
        return Response({"error":"Invalid GPS position"},status=400)
    token=str(request.data.get("qr_token",""))
    qr_ok=False
    if token:
        try:
            data=signing.loads(token,salt="armstrong-facility-qr-v1")
            qr_ok=data.get("facility_id")==str(stop.facility_id)
        except signing.BadSignature:
            pass
    if not qr_ok:
        return Response({"error":"Valid QR token for this facility is required"},status=400)
    f=stop.facility
    dist=None
    within=None
    if f.latitude is not None and f.longitude is not None:
        dist=distance_m(lat,lon,f.latitude,f.longitude)
        within=dist<=RADIUS_METRES and accuracy<=100
        if not within:
            return Response({"error":"Location is outside the 150m facility geofence or GPS accuracy exceeds 100m",
                             "distance_m":round(dist),"accuracy_m":accuracy},status=409)
    else:
        return Response({"error":"Facility coordinates must be configured before verification"},status=409)
    with transaction.atomic():
        existing=StopVerification.objects.select_for_update().filter(trip_stop=stop).first()
        if existing:
            if existing.event_id==event:return Response({"verified":True,"duplicate":True,"verification_id":str(existing.id)})
            return Response({"error":"Stop already verified"},status=409)
        try:
            v=StopVerification.objects.create(trip_stop=stop,driver=request.user,event_id=event,latitude=lat,
                longitude=lon,accuracy_m=accuracy,distance_m=dist,within_geofence=within,qr_verified=qr_ok,
                notes=str(request.data.get("notes",""))[:1000])
        except IntegrityError:
            return Response({"error":"Verification event already used"},status=409)
        stop.status="completed"
        stop.arrived_at=stop.arrived_at or timezone.now()
        stop.completed_at=timezone.now()
        stop.save(update_fields=["status","arrived_at","completed_at"])
        log(request.user,"fleet.stop.verified",v)
    return Response({"verified":True,"verification_id":str(v.id),"distance_m":round(dist),"qr_verified":True},status=201)

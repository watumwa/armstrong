"""Fleet foundation API: assignments and planned trips, no background GPS."""
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.decorators import api_view
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from .fleet_models import Vehicle, DriverAssignment, FleetTrip, TripStop, TrackingSession
from .models import StaffUser, Facility
from .views import check_role, log

def error(message, code=400):
    return Response({"error": message}, status=code)

def vehicle_json(v):
    return {"id": str(v.pk), "registration": v.registration, "label": v.label, "status": v.status}

def assignment_json(a):
    return {"id": str(a.pk), "vehicle_id": str(a.vehicle_id), "driver_id": str(a.driver_id), "driver_name": a.driver.name}

def trip_json(t):
    return {"id": str(t.pk), "vehicle_id": str(t.vehicle_id), "registration": t.vehicle.registration,
            "driver_id": str(t.driver_id), "driver_name": t.driver.name, "status": t.status,
            "scheduled_for": t.scheduled_for.isoformat(),
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "ended_at": t.ended_at.isoformat() if t.ended_at else None,
            "stops": [{"id": str(s.pk), "sequence": s.sequence, "facility_id": str(s.facility_id),
                       "facility_name": s.facility.name, "status": s.status} for s in t.stops.all()]}

@api_view(["GET", "POST"])
def vehicles(request):
    check_role(request.user, "Administrator", "Supervisor", "Waste Collector")
    if request.method == "GET":
        return Response({"vehicles": [vehicle_json(v) for v in Vehicle.objects.order_by("registration")]})
    check_role(request.user, "Administrator", "Supervisor")
    reg = str(request.data.get("registration", "")).strip().upper()
    label = str(request.data.get("label", "")).strip()
    if not (3 <= len(reg) <= 32 and 2 <= len(label) <= 120):
        return error("Valid registration and label required")
    try:
        with transaction.atomic():
            v = Vehicle.objects.create(registration=reg, label=label)
            log(request.user, "fleet.vehicle.created", v)
    except IntegrityError:
        return error("Registration already exists", 409)
    return Response({"vehicle": vehicle_json(v)}, status=201)

@api_view(["GET"])
def drivers(request):
    check_role(request.user, "Administrator", "Supervisor")
    return Response({"drivers": [{"id": str(u.pk), "name": u.name} for u in
                                 StaffUser.objects.filter(active=True, role="Waste Collector").order_by("name")]})

@api_view(["GET", "POST"])
def assignments(request):
    check_role(request.user, "Administrator", "Supervisor", "Waste Collector")
    if request.method == "GET":
        q = DriverAssignment.objects.select_related("driver").filter(ended_at__isnull=True)
        if request.user.role == "Waste Collector":
            q = q.filter(driver=request.user)
        return Response({"assignments": [assignment_json(a) for a in q]})
    check_role(request.user, "Administrator", "Supervisor")
    try:
        vehicle = Vehicle.objects.get(pk=request.data.get("vehicle_id"), status="available")
        driver = StaffUser.objects.get(pk=request.data.get("driver_id"), role="Waste Collector", active=True)
    except (Vehicle.DoesNotExist, StaffUser.DoesNotExist, ValueError, TypeError):
        return error("Select an available vehicle and active collector")
    try:
        with transaction.atomic():
            a = DriverAssignment.objects.create(vehicle=vehicle, driver=driver, assigned_by=request.user)
            log(request.user, "fleet.assignment.created", a)
    except IntegrityError:
        return error("Vehicle or driver is already assigned", 409)
    return Response({"assignment": assignment_json(a)}, status=201)

@api_view(["POST"])
def end_assignment(request, assignment_id):
    check_role(request.user, "Administrator", "Supervisor")
    with transaction.atomic():
        a = DriverAssignment.objects.select_for_update().filter(pk=assignment_id, ended_at__isnull=True).first()
        if not a:
            return error("Assignment not found", 404)
        if FleetTrip.objects.filter(vehicle=a.vehicle, driver=a.driver, status="active").exists():
            return error("Complete active trip first", 409)
        a.ended_at = timezone.now()
        a.save(update_fields=["ended_at"])
        log(request.user, "fleet.assignment.ended", a)
    return Response({"ok": True})

@api_view(["GET", "POST"])
def trips(request):
    check_role(request.user, "Administrator", "Supervisor", "Waste Collector")
    if request.method == "GET":
        q = FleetTrip.objects.select_related("vehicle", "driver").prefetch_related("stops__facility").order_by("-scheduled_for")
        if request.user.role == "Waste Collector":
            q = q.filter(driver=request.user)
        return Response({"trips": [trip_json(t) for t in q[:100]]})
    check_role(request.user, "Administrator", "Supervisor")
    when = parse_datetime(str(request.data.get("scheduled_for", "")))
    if not when or timezone.is_naive(when):
        return error("Scheduled date must include a timezone offset")
    stops = request.data.get("facility_ids")
    if not isinstance(stops, list) or not 1 <= len(stops) <= 30 or len(set(map(str, stops))) != len(stops):
        return error("Provide 1 to 30 unique facility IDs")
    try:
        vehicle = Vehicle.objects.get(pk=request.data.get("vehicle_id"), status="available")
        driver = StaffUser.objects.get(pk=request.data.get("driver_id"), role="Waste Collector", active=True)
        found = list(Facility.objects.filter(pk__in=stops))
    except (Vehicle.DoesNotExist, StaffUser.DoesNotExist, ValueError, TypeError):
        return error("Invalid vehicle or driver")
    if len(found) != len(stops):
        return error("One or more facilities were not found")
    if not DriverAssignment.objects.filter(vehicle=vehicle, driver=driver, ended_at__isnull=True).exists():
        return error("Driver must be assigned to vehicle", 409)
    lookup = {str(f.pk): f for f in found}
    with transaction.atomic():
        trip = FleetTrip.objects.create(vehicle=vehicle, driver=driver, created_by=request.user, scheduled_for=when)
        TripStop.objects.bulk_create([TripStop(trip=trip, facility=lookup[str(fid)], sequence=i)
                                      for i, fid in enumerate(stops, 1)])
        log(request.user, "fleet.trip.created", trip)
    trip = FleetTrip.objects.select_related("vehicle", "driver").prefetch_related("stops__facility").get(pk=trip.pk)
    return Response({"trip": trip_json(trip)}, status=201)

@api_view(["POST"])
def trip_action(request, trip_id, operation):
    if operation not in ("start", "complete", "cancel"):
        return error("Unknown trip action", 404)
    with transaction.atomic():
        trip = FleetTrip.objects.select_for_update().select_related("vehicle", "driver").filter(pk=trip_id).first()
        if not trip:
            return error("Trip not found", 404)
        if operation == "cancel":
            check_role(request.user, "Administrator", "Supervisor")
            if trip.status != "planned":
                return error("Only planned trips can be cancelled", 409)
            trip.status = "cancelled"
        else:
            if request.user.role != "Administrator" and request.user.pk != trip.driver_id:
                raise PermissionDenied("Only the assigned driver can manage this trip")
            if operation == "start":
                if trip.status != "planned":
                    return error("Trip is not planned", 409)
                if not DriverAssignment.objects.filter(vehicle=trip.vehicle, driver=trip.driver, ended_at__isnull=True).exists():
                    return error("Driver assignment has ended", 409)
                if FleetTrip.objects.filter(status="active", vehicle=trip.vehicle).exclude(pk=trip.pk).exists() or FleetTrip.objects.filter(status="active", driver=trip.driver).exclude(pk=trip.pk).exists():
                    return error("Vehicle or driver already has an active trip", 409)
                trip.status = "active"
                trip.started_at = timezone.now()
            else:
                if trip.status != "active":
                    return error("Trip is not active", 409)
                trip.status = "completed"
                trip.ended_at = timezone.now()
                TrackingSession.objects.filter(trip=trip,stopped_at__isnull=True).update(
                    stopped_at=trip.ended_at, stop_reason="trip_completed"
                )
        try:
            trip.save()
        except IntegrityError:
            return error("Conflicting active trip", 409)
        log(request.user, "fleet.trip." + operation, trip)
    trip = FleetTrip.objects.select_related("vehicle", "driver").prefetch_related("stops__facility").get(pk=trip.pk)
    return Response({"trip": trip_json(trip)})

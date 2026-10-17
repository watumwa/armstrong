"""Marketer visits: planned work, phone GPS check-ins, visit forms and review."""
import math
from collections import defaultdict

from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .fleet_verification import distance_m
from .models import Facility, MarketingVisit, StaffUser
from .views import check_role, log


MANAGERS = ("Administrator", "Supervisor")


def visit_data(visit):
    return {
        "id": str(visit.id), "marketer_id": str(visit.marketer_id), "marketer_name": visit.marketer.name,
        "facility_id": str(visit.facility_id) if visit.facility_id else None,
        "facility_name": visit.facility.name if visit.facility_id else None,
        "client_name": visit.client_name, "client_phone": visit.client_phone, "address": visit.address,
        "planned_for": visit.planned_for.isoformat(), "status": visit.status,
        "checked_in_at": visit.checked_in_at.isoformat() if visit.checked_in_at else None,
        "check_in": ({"latitude": visit.check_in_latitude, "longitude": visit.check_in_longitude,
                      "accuracy_m": visit.check_in_accuracy_m} if visit.checked_in_at else None),
        "contact_name": visit.contact_name, "contact_phone": visit.contact_phone, "outcome": visit.outcome,
        "notes": visit.notes, "follow_up_on": visit.follow_up_on.isoformat() if visit.follow_up_on else None,
        "submitted_at": visit.submitted_at.isoformat() if visit.submitted_at else None,
        "reviewed_at": visit.reviewed_at.isoformat() if visit.reviewed_at else None,
        "review_notes": visit.review_notes,
    }


def _position(data):
    try:
        latitude, longitude, accuracy = float(data.get("latitude")), float(data.get("longitude")), float(data.get("accuracy_m"))
    except (TypeError, ValueError, OverflowError):
        raise ValueError("Valid GPS coordinates and accuracy are required")
    if not all(math.isfinite(value) for value in (latitude, longitude, accuracy)):
        raise ValueError("Valid GPS coordinates and accuracy are required")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180 and 0 <= accuracy <= 1000):
        raise ValueError("GPS coordinates or accuracy are out of range")
    return latitude, longitude, accuracy


@api_view(["GET"])
def marketers(request):
    check_role(request.user, *MANAGERS)
    rows = StaffUser.objects.filter(role="Marketer", active=True).order_by("name")
    return Response({"marketers": [{"id": str(row.id), "name": row.name} for row in rows]})


@api_view(["GET", "POST"])
def visits(request):
    if request.user.role not in (*MANAGERS, "Marketer"):
        return Response({"error": "Marketer or supervisor access required"}, status=403)
    if request.method == "GET":
        rows = MarketingVisit.objects.select_related("marketer", "facility").order_by("-planned_for")
        if request.user.role == "Marketer":
            rows = rows.filter(marketer=request.user)
        return Response({"visits": [visit_data(row) for row in rows[:200]]})

    check_role(request.user, *MANAGERS)
    when = parse_datetime(str(request.data.get("planned_for", "")))
    if not when or timezone.is_naive(when):
        return Response({"error": "Planned date and time must include a timezone offset"}, status=400)
    try:
        marketer = StaffUser.objects.get(pk=request.data.get("marketer_id"), role="Marketer", active=True)
    except (StaffUser.DoesNotExist, ValueError, TypeError):
        return Response({"error": "Select an active marketer"}, status=400)
    facility = None
    raw_facility = request.data.get("facility_id")
    if raw_facility:
        try:
            facility = Facility.objects.get(pk=raw_facility)
        except (Facility.DoesNotExist, ValueError, TypeError):
            return Response({"error": "Selected facility was not found"}, status=400)
    client_name = facility.name if facility else str(request.data.get("client_name", "")).strip()
    client_phone = facility.phone if facility else str(request.data.get("client_phone", "")).strip()
    address = facility.address if facility else str(request.data.get("address", "")).strip()
    if len(client_name) < 2 or len(client_name) > 200 or len(address) > 300:
        return Response({"error": "A client name and valid address are required"}, status=400)
    visit = MarketingVisit.objects.create(
        marketer=marketer, facility=facility, planned_by=request.user, client_name=client_name,
        client_phone=client_phone[:40], address=address, planned_for=when,
    )
    log(request.user, "field.visit.planned", visit)
    visit = MarketingVisit.objects.select_related("marketer", "facility").get(pk=visit.pk)
    return Response({"visit": visit_data(visit)}, status=201)


@api_view(["POST"])
def check_in(request, visit_id):
    check_role(request.user, "Marketer")
    visit = get_object_or_404(MarketingVisit.objects.select_related("facility", "marketer"), pk=visit_id, marketer=request.user)
    if visit.status != "scheduled":
        return Response({"error": "Only a scheduled visit can be checked in"}, status=409)
    try:
        latitude, longitude, accuracy = _position(request.data)
    except ValueError as exc:
        return Response({"error": str(exc)}, status=400)
    if visit.facility_id and visit.facility.latitude is not None and visit.facility.longitude is not None:
        distance = distance_m(latitude, longitude, visit.facility.latitude, visit.facility.longitude)
        if distance > 200 or accuracy > 100:
            return Response({"error": "Check-in is outside the 200m facility area or phone GPS is inaccurate",
                             "distance_m": round(distance), "accuracy_m": accuracy}, status=409)
    visit.check_in_latitude, visit.check_in_longitude, visit.check_in_accuracy_m = latitude, longitude, accuracy
    visit.checked_in_at, visit.status = timezone.now(), "checked_in"
    visit.save(update_fields=["check_in_latitude", "check_in_longitude", "check_in_accuracy_m", "checked_in_at", "status"])
    log(request.user, "field.visit.checked_in", visit)
    return Response({"visit": visit_data(visit)})


@api_view(["POST"])
def submit_visit(request, visit_id):
    check_role(request.user, "Marketer")
    visit = get_object_or_404(MarketingVisit.objects.select_related("facility", "marketer"), pk=visit_id, marketer=request.user)
    if visit.status != "checked_in":
        return Response({"error": "Check in from the staff phone before submitting a visit"}, status=409)
    outcome = str(request.data.get("outcome", "")).strip()
    notes = str(request.data.get("notes", "")).strip()
    follow_up = request.data.get("follow_up_on")
    follow_up_on = parse_date(str(follow_up)) if follow_up else None
    if len(outcome) < 2 or len(outcome) > 120 or len(notes) < 2 or len(notes) > 2000 or (follow_up and not follow_up_on):
        return Response({"error": "Provide an outcome, meaningful notes and a valid follow-up date when supplied"}, status=400)
    visit.contact_name = str(request.data.get("contact_name", "")).strip()[:160]
    visit.contact_phone = str(request.data.get("contact_phone", "")).strip()[:40]
    visit.outcome, visit.notes, visit.follow_up_on = outcome, notes, follow_up_on
    visit.submitted_at, visit.status = timezone.now(), "submitted"
    visit.save(update_fields=["contact_name", "contact_phone", "outcome", "notes", "follow_up_on", "submitted_at", "status"])
    log(request.user, "field.visit.submitted", visit)
    return Response({"visit": visit_data(visit)})


@api_view(["POST"])
def review_visit(request, visit_id):
    check_role(request.user, *MANAGERS)
    visit = get_object_or_404(MarketingVisit.objects.select_related("facility", "marketer"), pk=visit_id)
    if visit.status != "submitted":
        return Response({"error": "Only submitted visits can be reviewed"}, status=409)
    decision = request.data.get("decision")
    if decision not in ("approve", "return"):
        return Response({"error": "Decision must be approve or return"}, status=400)
    visit.reviewed_by, visit.reviewed_at = request.user, timezone.now()
    visit.review_notes = str(request.data.get("review_notes", "")).strip()[:1000]
    visit.status = "approved" if decision == "approve" else "checked_in"
    visit.save(update_fields=["reviewed_by", "reviewed_at", "review_notes", "status"])
    log(request.user, f"field.visit.{decision}d", visit)
    return Response({"visit": visit_data(visit)})


@api_view(["GET"])
def supervisor_summary(request):
    check_role(request.user, *MANAGERS)
    today = timezone.localdate()
    rows = MarketingVisit.objects.select_related("marketer").filter(planned_for__date=today)
    statuses = {row["status"]: row["total"] for row in rows.values("status").annotate(total=Count("id"))}
    people = defaultdict(lambda: {"marketer_id": "", "marketer_name": "", "planned": 0, "checked_in": 0, "submitted": 0, "approved": 0})
    for visit in rows:
        item = people[str(visit.marketer_id)]
        item["marketer_id"], item["marketer_name"] = str(visit.marketer_id), visit.marketer.name
        item["planned"] += 1
        if visit.checked_in_at:
            item["checked_in"] += 1
        if visit.submitted_at:
            item["submitted"] += 1
        if visit.status == "approved":
            item["approved"] += 1
    return Response({"date": today.isoformat(), "visits_by_status": statuses, "marketers": list(people.values())})

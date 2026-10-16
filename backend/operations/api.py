"""Same-origin API contract served by the Django service.

The browser continues to call `/api/...`; Vercel Services routes that namespace
to this Django application. Keeping the response envelopes stable prevents a
frontend/backend release from drifting during the migration away from Next API
route handlers.
"""

import os
import uuid
from datetime import timedelta

import bcrypt
import jwt
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Collection, Facility, Payment, StaffUser
from .serializers import CollectionSerializer, FacilitySerializer, PaymentSerializer, StaffSerializer
from .views import check_role, log


SESSION_COOKIE = "armstrong_session"
SESSION_DURATION = timedelta(hours=8)
ROLES = {"Administrator", "Supervisor", "Waste Collector", "Revenue Officer"}


def _error(message, code=status.HTTP_400_BAD_REQUEST):
    return Response({"error": message}, status=code)


def _session_user(user):
    return {"id": str(user.pk), "name": user.name, "role": user.role}


def _issue_session(user):
    now = timezone.now()
    secret = os.environ.get("AUTH_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("AUTH_SECRET must be at least 32 characters")

    return jwt.encode(
        {
            "sub": str(user.pk),
            "name": user.name,
            "role": user.role,
            "iat": now,
            "exp": now + SESSION_DURATION,
        },
        secret,
        algorithm="HS256",
    )


def _set_session(response, user):
    response.set_cookie(
        SESSION_COOKIE,
        _issue_session(user),
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/",
    )
    return response


def _collection_data(instance):
    data = CollectionSerializer(instance).data
    data["facility_id"] = data["facility"]
    data["collector_id"] = data["collector"]
    data["verified_by_id"] = data["verified_by"]
    if hasattr(instance, "facility"):
        data["facility_name"] = instance.facility.name
    return data


def _payment_data(instance):
    data = PaymentSerializer(instance).data
    data["facility_id"] = data["facility"]
    data["received_by_id"] = data["received_by"]
    return data


@api_view(["GET"])
@permission_classes([AllowAny])
def health(_request):
    return Response(
        {
            "service": "armstrong-django",
            "status": "online",
            "databaseConfigured": bool(os.environ.get("DATABASE_URL")),
            "authenticationConfigured": bool(os.environ.get("AUTH_SECRET")),
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    email = str(request.data.get("email", "")).strip().lower()
    password = str(request.data.get("password", ""))
    if not email or not password:
        return _error("Email and password required")

    user = StaffUser.objects.filter(email=email).first()
    stored_hash = user.password_hash.encode("utf-8") if user else b"$2b$12$000000000000000000000uGMDP.3ChZg6LS3iW6eX0wUk0u6P4BW"
    try:
        valid = bcrypt.checkpw(password.encode("utf-8"), stored_hash)
    except (TypeError, ValueError):
        valid = False
    if not user or not valid or not user.active:
        return _error("Invalid credentials", status.HTTP_401_UNAUTHORIZED)

    return _set_session(Response({"user": _session_user(user)}), user)


@api_view(["POST"])
@permission_classes([AllowAny])
def logout(_request):
    response = Response({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="Lax")
    return response


@api_view(["GET"])
def me(request):
    return Response({"user": _session_user(request.user)})


@api_view(["POST"])
def change_password(request):
    old_password = str(request.data.get("oldPassword", ""))
    new_password = str(request.data.get("newPassword", ""))
    if len(new_password) < 12:
        return _error("New password must be 12+ characters")

    try:
        valid = bcrypt.checkpw(old_password.encode("utf-8"), request.user.password_hash.encode("utf-8"))
    except (TypeError, ValueError):
        valid = False
    if not valid:
        return _error("Current password is incorrect", status.HTTP_403_FORBIDDEN)

    request.user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    request.user.save(update_fields=["password_hash"])
    log(request.user, "user.password_changed", request.user)
    return Response({"ok": True})


@api_view(["GET", "POST"])
def facilities(request):
    if request.method == "GET":
        queryset = Facility.objects.all().order_by("name")
        return Response({"facilities": FacilitySerializer(queryset, many=True).data})

    check_role(request.user, "Administrator", "Supervisor")
    serializer = FacilitySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    facility = serializer.save(code="AGS-" + uuid.uuid4().hex[:10].upper())
    log(request.user, "facility.created", facility)
    return Response({"facility": FacilitySerializer(facility).data}, status=status.HTTP_201_CREATED)


@api_view(["GET", "PATCH"])
def facility_detail(request, facility_id):
    facility = get_object_or_404(Facility, pk=facility_id)
    if request.method == "GET":
        return Response({"facility": FacilitySerializer(facility).data})

    check_role(request.user, "Administrator", "Supervisor")
    serializer = FacilitySerializer(facility, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    facility = serializer.save()
    log(request.user, "facility.updated", facility)
    return Response({"facility": FacilitySerializer(facility).data})


@api_view(["GET", "POST"])
def users(request):
    check_role(request.user, "Administrator")
    if request.method == "GET":
        return Response({"users": StaffSerializer(StaffUser.objects.all().order_by("-created_at"), many=True).data})

    name = str(request.data.get("name", "")).strip()
    email = str(request.data.get("email", "")).strip().lower()
    role = str(request.data.get("role", ""))
    password = str(request.data.get("password", ""))
    if len(name) < 2 or role not in ROLES or len(password) < 12:
        return _error("Valid name, email, role and password (12+ characters) required")
    try:
        validate_email(email)
    except DjangoValidationError:
        return _error("Valid name, email, role and password (12+ characters) required")

    try:
        user = StaffUser.objects.create(
            name=name,
            email=email,
            role=role,
            password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8"),
        )
    except IntegrityError:
        return _error("Email already registered", status.HTTP_409_CONFLICT)
    log(request.user, "user.created", user)
    return Response({"user": StaffSerializer(user).data}, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def collections(request):
    if request.method == "GET":
        queryset = Collection.objects.select_related("facility").all().order_by("-scheduled_at")
        if request.user.role == "Waste Collector":
            queryset = queryset.filter(collector=request.user)
        return Response({"collections": [_collection_data(item) for item in queryset[:200]]})

    check_role(request.user, "Administrator", "Supervisor")
    payload = request.data.copy()
    payload["facility"] = payload.pop("facility_id", payload.get("facility", None))
    payload["collector"] = payload.pop("collector_id", payload.get("collector", None))
    serializer = CollectionSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    collection = serializer.save()
    log(request.user, "collection.scheduled", collection)
    collection = Collection.objects.select_related("facility").get(pk=collection.pk)
    return Response({"collection": _collection_data(collection)}, status=status.HTTP_201_CREATED)


@api_view(["GET", "POST"])
def payments(request):
    check_role(request.user, "Administrator", "Supervisor", "Revenue Officer")
    if request.method == "GET":
        queryset = Payment.objects.select_related("facility").all().order_by("-paid_at")[:200]
        return Response({"payments": [_payment_data(item) for item in queryset]})

    check_role(request.user, "Administrator", "Revenue Officer")
    payload = request.data.copy()
    payload["facility"] = payload.pop("facility_id", payload.get("facility", None))
    amount = payload.get("amount")
    if payload.get("method") not in {"Cash", "Mobile Money", "Bank Transfer"}:
        return _error("Invalid payment details")
    try:
        if float(amount) <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return _error("Invalid payment details")

    serializer = PaymentSerializer(data=payload)
    serializer.is_valid(raise_exception=True)
    payment = serializer.save(
        reference="AGP-" + uuid.uuid4().hex[:12].upper(),
        received_by=request.user,
        status="pending",
        paid_at=timezone.now(),
    )
    log(request.user, "payment.recorded_pending", payment)
    return Response(
        {"payment": _payment_data(payment), "message": "Pending payment recorded. Not confirmed until reconciled."},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
def report_summary(request):
    check_role(request.user, "Administrator", "Supervisor", "Revenue Officer")
    return Response(
        {
            "facility_count": Facility.objects.count(),
            "contracted_monthly": Facility.objects.aggregate(total=Sum("monthly_fee"))["total"] or 0,
            "collections": list(Collection.objects.values("status").annotate(total=Count("id"))),
            "payments_received": Payment.objects.filter(status="confirmed").aggregate(total=Sum("amount"))["total"] or 0,
            "currency": "UGX",
        }
    )

"""Fleet Phase 1 models. Tables are created by backend/schema.sql."""
import uuid
from django.db import models
from .models import StaffUser, Facility

class Vehicle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.TextField(unique=True)
    label = models.TextField()
    status = models.TextField(default="available")
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        managed = False
        db_table = "fleet_vehicles"

class DriverAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    driver = models.ForeignKey(StaffUser, on_delete=models.PROTECT, related_name="driver_assignments")
    assigned_by = models.ForeignKey(StaffUser, on_delete=models.PROTECT, related_name="created_driver_assignments")
    assigned_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = "fleet_assignments"

class FleetTrip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    driver = models.ForeignKey(StaffUser, on_delete=models.PROTECT, related_name="fleet_trips")
    created_by = models.ForeignKey(StaffUser, on_delete=models.PROTECT, related_name="created_fleet_trips")
    status = models.TextField(default="planned")
    scheduled_for = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        managed = False
        db_table = "fleet_trips"

class TripStop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(FleetTrip, on_delete=models.PROTECT, related_name="stops")
    facility = models.ForeignKey(Facility, on_delete=models.PROTECT)
    sequence = models.PositiveIntegerField()
    status = models.TextField(default="pending")
    arrived_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        managed = False
        db_table = "fleet_trip_stops"

class LocationPing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip = models.ForeignKey(FleetTrip, on_delete=models.PROTECT, related_name="location_pings")
    driver = models.ForeignKey(StaffUser, on_delete=models.PROTECT)
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy_m = models.FloatField()
    captured_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    client_event_id = models.UUIDField(unique=True)
    class Meta:
        managed = False
        db_table = "fleet_location_pings"

class StopVerification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    trip_stop = models.OneToOneField(TripStop, on_delete=models.PROTECT, related_name="verification")
    driver = models.ForeignKey(StaffUser, on_delete=models.PROTECT)
    event_id = models.UUIDField(unique=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy_m = models.FloatField()
    distance_m = models.FloatField(null=True)
    within_geofence = models.BooleanField(null=True)
    qr_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(default="")
    class Meta:
        managed = False
        db_table = "fleet_stop_verifications"

class FleetSyncEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey(StaffUser, on_delete=models.PROTECT)
    client_event_id = models.UUIDField()
    event_type = models.TextField()
    trip_stop = models.ForeignKey(TripStop, on_delete=models.PROTECT)
    status = models.TextField()
    result = models.JSONField(default=dict)
    received_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        managed = False
        db_table = "fleet_sync_events"
        constraints = [models.UniqueConstraint(fields=["driver", "client_event_id"], name="fleet_sync_driver_event_unique")]

class FleetAlert(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    alert_key = models.TextField(unique=True)
    trip = models.ForeignKey(FleetTrip, null=True, on_delete=models.PROTECT)
    severity = models.TextField()
    category = models.TextField()
    message = models.TextField()
    resolved_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        managed = False
        db_table = "fleet_alerts"

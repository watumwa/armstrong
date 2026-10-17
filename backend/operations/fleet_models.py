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

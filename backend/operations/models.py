import uuid
from django.db import models
class StaffUser(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 name=models.TextField()
 email=models.TextField(unique=True)
 role=models.TextField()
 password_hash=models.TextField()
 active=models.BooleanField(default=True)
 created_at=models.DateTimeField(auto_now_add=True)
 @property
 def is_authenticated(self):return True
 class Meta:db_table="users";managed=False
class Facility(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 code=models.TextField(unique=True)
 name=models.TextField()
 type=models.TextField()
 address=models.TextField()
 district=models.TextField()
 phone=models.TextField()
 latitude=models.FloatField(null=True,blank=True)
 longitude=models.FloatField(null=True,blank=True)
 monthly_fee=models.DecimalField(max_digits=12,decimal_places=2,default=0)
 collection_day=models.TextField(null=True,blank=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="facilities";managed=False
class Agreement(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 facility=models.ForeignKey(Facility,on_delete=models.PROTECT)
 reference=models.TextField(unique=True)
 status=models.TextField(default="draft")
 start_date=models.DateField(null=True,blank=True)
 end_date=models.DateField(null=True,blank=True)
 monthly_fee=models.DecimalField(max_digits=12,decimal_places=2)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="agreements";managed=False
class Collection(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 facility=models.ForeignKey(Facility,on_delete=models.PROTECT)
 collector=models.ForeignKey(StaffUser,on_delete=models.PROTECT,null=True,related_name="assigned_collections")
 scheduled_at=models.DateTimeField()
 status=models.TextField(default="scheduled")
 waste_category=models.TextField(null=True,blank=True)
 bags=models.IntegerField(null=True,blank=True)
 weight_kg=models.DecimalField(max_digits=12,decimal_places=3,null=True,blank=True)
 notes=models.TextField(null=True,blank=True)
 verified_by=models.ForeignKey(StaffUser,on_delete=models.PROTECT,null=True,related_name="verified_collections")
 verified_at=models.DateTimeField(null=True,blank=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="collections";managed=False
class Payment(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 facility=models.ForeignKey(Facility,on_delete=models.PROTECT)
 received_by=models.ForeignKey(StaffUser,on_delete=models.PROTECT,null=True)
 amount=models.DecimalField(max_digits=12,decimal_places=2)
 method=models.TextField()
 reference=models.TextField(unique=True)
 status=models.TextField(default="pending")
 paid_at=models.DateTimeField()
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="payments";managed=False
class AuditLog(models.Model):
 id=models.BigAutoField(primary_key=True)
 actor=models.ForeignKey(StaffUser,on_delete=models.PROTECT,null=True)
 action=models.TextField()
 entity_type=models.TextField()
 entity_id=models.TextField()
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="audit_log";managed=False

# Register fleet models with Django's application model loader.
from .fleet_models import Vehicle, DriverAssignment, FleetTrip, TripStop, LocationPing, StopVerification, FleetSyncEvent, FleetAlert  # noqa: E402,F401

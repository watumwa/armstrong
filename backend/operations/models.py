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
 sms_opt_in=models.BooleanField(default=False)
 sms_opt_in_at=models.DateTimeField(null=True,blank=True)
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
class Invoice(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 facility=models.ForeignKey(Facility,on_delete=models.PROTECT,related_name="invoices")
 invoice_number=models.TextField(unique=True)
 issue_date=models.DateField()
 due_date=models.DateField()
 status=models.TextField(default="issued")
 currency=models.TextField(default="UGX")
 subtotal=models.DecimalField(max_digits=12,decimal_places=2,default=0)
 amount_paid=models.DecimalField(max_digits=12,decimal_places=2,default=0)
 balance=models.DecimalField(max_digits=12,decimal_places=2,default=0)
 notes=models.TextField(default="")
 created_by=models.ForeignKey(StaffUser,on_delete=models.PROTECT,related_name="created_invoices")
 issued_at=models.DateTimeField(null=True,blank=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="invoices";managed=False
class InvoiceLine(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 invoice=models.ForeignKey(Invoice,on_delete=models.PROTECT,related_name="lines")
 description=models.TextField()
 quantity=models.DecimalField(max_digits=12,decimal_places=3)
 unit_price=models.DecimalField(max_digits=12,decimal_places=2)
 line_total=models.DecimalField(max_digits=12,decimal_places=2)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="invoice_lines";managed=False
class PaymentAllocation(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 payment=models.ForeignKey(Payment,on_delete=models.PROTECT,related_name="allocations")
 invoice=models.ForeignKey(Invoice,on_delete=models.PROTECT,related_name="allocations")
 amount=models.DecimalField(max_digits=12,decimal_places=2)
 allocated_by=models.ForeignKey(StaffUser,on_delete=models.PROTECT,related_name="payment_allocations")
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="payment_allocations";managed=False
class SMSReminder(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 reminder_key=models.TextField(unique=True)
 facility=models.ForeignKey(Facility,on_delete=models.PROTECT,related_name="sms_reminders")
 collection=models.ForeignKey(Collection,on_delete=models.PROTECT,null=True,blank=True,related_name="sms_reminders")
 invoice=models.ForeignKey(Invoice,on_delete=models.PROTECT,null=True,blank=True,related_name="sms_reminders")
 kind=models.TextField()
 recipient_phone=models.TextField()
 message=models.TextField()
 scheduled_for=models.DateTimeField()
 status=models.TextField(default="queued")
 provider_reference=models.TextField(null=True,blank=True)
 last_error=models.TextField(null=True,blank=True)
 sent_at=models.DateTimeField(null=True,blank=True)
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="sms_reminders";managed=False
class MarketingVisit(models.Model):
 id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
 marketer=models.ForeignKey(StaffUser,on_delete=models.PROTECT,related_name="marketing_visits")
 facility=models.ForeignKey(Facility,on_delete=models.PROTECT,null=True,blank=True,related_name="marketing_visits")
 planned_by=models.ForeignKey(StaffUser,on_delete=models.PROTECT,related_name="planned_marketing_visits")
 client_name=models.TextField()
 client_phone=models.TextField(default="")
 address=models.TextField(default="")
 planned_for=models.DateTimeField()
 status=models.TextField(default="scheduled")
 check_in_latitude=models.FloatField(null=True,blank=True)
 check_in_longitude=models.FloatField(null=True,blank=True)
 check_in_accuracy_m=models.FloatField(null=True,blank=True)
 checked_in_at=models.DateTimeField(null=True,blank=True)
 contact_name=models.TextField(default="")
 contact_phone=models.TextField(default="")
 outcome=models.TextField(default="")
 notes=models.TextField(default="")
 follow_up_on=models.DateField(null=True,blank=True)
 submitted_at=models.DateTimeField(null=True,blank=True)
 reviewed_by=models.ForeignKey(StaffUser,on_delete=models.PROTECT,null=True,blank=True,related_name="reviewed_marketing_visits")
 reviewed_at=models.DateTimeField(null=True,blank=True)
 review_notes=models.TextField(default="")
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="marketing_visits";managed=False
class AuditLog(models.Model):
 id=models.BigAutoField(primary_key=True)
 actor=models.ForeignKey(StaffUser,on_delete=models.PROTECT,null=True)
 action=models.TextField()
 entity_type=models.TextField()
 entity_id=models.TextField()
 created_at=models.DateTimeField(auto_now_add=True)
 class Meta:db_table="audit_log";managed=False

# Register fleet models with Django's application model loader.
from .fleet_models import Vehicle, DriverAssignment, FleetTrip, TripStop, LocationPing, StopVerification, FleetSyncEvent, FleetAlert, TrackingSession  # noqa: E402,F401

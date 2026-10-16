import uuid
from decimal import Decimal
from django.db import transaction
from django.db.models import Count,Sum
from django.utils import timezone
from rest_framework import status,viewsets
from rest_framework.decorators import api_view,permission_classes,action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied,ValidationError
from .models import Facility,Agreement,Collection,Payment,StaffUser,AuditLog
from .serializers import FacilitySerializer,AgreementSerializer,CollectionSerializer,PaymentSerializer,StaffSerializer
def check_role(user,*roles):
 if user.role not in roles:raise PermissionDenied("Insufficient role permissions")
def log(user,action,instance):
 AuditLog.objects.create(actor=user,action=action,entity_type=instance.__class__.__name__,entity_id=str(instance.pk))
class FacilityViewSet(viewsets.ModelViewSet):
 queryset=Facility.objects.all().order_by("name")
 serializer_class=FacilitySerializer
 def perform_create(self,serializer):
  check_role(self.request.user,"Administrator","Supervisor")
  obj=serializer.save(code="AGS-"+uuid.uuid4().hex[:10].upper());log(self.request.user,"facility.created",obj)
 def perform_update(self,serializer):
  check_role(self.request.user,"Administrator","Supervisor")
  obj=serializer.save();log(self.request.user,"facility.updated",obj)
 def perform_destroy(self,instance):raise PermissionDenied("Facility deletion is disabled; archive instead.")
class AgreementViewSet(viewsets.ModelViewSet):
 queryset=Agreement.objects.select_related("facility").all().order_by("-created_at")
 serializer_class=AgreementSerializer
 def perform_create(self,serializer):
  check_role(self.request.user,"Administrator","Supervisor")
  obj=serializer.save(reference="AGA-"+uuid.uuid4().hex[:10].upper());log(self.request.user,"agreement.created",obj)
 def perform_update(self,serializer):
  check_role(self.request.user,"Administrator","Supervisor")
  obj=serializer.save();log(self.request.user,"agreement.updated",obj)
 def perform_destroy(self,instance):raise PermissionDenied("Agreements must be terminated, not deleted.")
class CollectionViewSet(viewsets.ModelViewSet):
 serializer_class=CollectionSerializer
 def get_queryset(self):
  q=Collection.objects.select_related("facility","collector").all().order_by("-scheduled_at")
  return q.filter(collector=self.request.user) if self.request.user.role=="Waste Collector" else q
 def perform_create(self,serializer):
  check_role(self.request.user,"Administrator","Supervisor")
  obj=serializer.save();log(self.request.user,"collection.scheduled",obj)
 def perform_update(self,serializer):
  check_role(self.request.user,"Administrator","Supervisor")
  if self.get_object().status in ("verified",):raise ValidationError("Verified collections cannot be modified.")
  obj=serializer.save();log(self.request.user,"collection.updated",obj)
 def perform_destroy(self,instance):raise PermissionDenied("Collection records cannot be deleted.")
 @action(detail=True,methods=["post"])
 def submit(self,request,pk=None):
  check_role(request.user,"Waste Collector")
  obj=self.get_object()
  if obj.collector_id!=request.user.pk:raise PermissionDenied("Not assigned to this collection")
  if obj.status not in ("scheduled","en_route","arrived","rejected"):raise ValidationError("Collection cannot be submitted in this state")
  try:
   bags=int(request.data.get("bags"));weight=Decimal(str(request.data.get("weight_kg")))
   if bags<0 or weight<0:raise ValueError()
  except (ValueError,TypeError,ArithmeticError):raise ValidationError("Valid nonnegative bags and weight required")
  obj.bags=bags;obj.weight_kg=weight;obj.notes=str(request.data.get("notes",""))[:2000];obj.status="submitted"
  obj.save(update_fields=["bags","weight_kg","notes","status"]);log(request.user,"collection.submitted",obj)
  return Response(self.get_serializer(obj).data)
 @action(detail=True,methods=["post"])
 def verify(self,request,pk=None):
  check_role(request.user,"Administrator","Supervisor")
  obj=self.get_object()
  if obj.status!="submitted":raise ValidationError("Only submitted collections can be verified")
  decision=request.data.get("decision")
  if decision not in ("verified","rejected"):raise ValidationError("Decision must be verified or rejected")
  obj.status=decision;obj.verified_by=request.user;obj.verified_at=timezone.now()
  obj.save(update_fields=["status","verified_by","verified_at"]);log(request.user,"collection."+decision,obj)
  return Response(self.get_serializer(obj).data)
class PaymentViewSet(viewsets.ModelViewSet):
 serializer_class=PaymentSerializer
 http_method_names=["get","post","head","options"]
 def get_queryset(self):
  check_role(self.request.user,"Administrator","Supervisor","Revenue Officer")
  return Payment.objects.select_related("facility").all().order_by("-paid_at")
 def perform_create(self,serializer):
  check_role(self.request.user,"Administrator","Revenue Officer")
  if serializer.validated_data["amount"]<=0:raise ValidationError("Amount must be positive")
  if serializer.validated_data["method"] not in ("Cash","Mobile Money","Bank Transfer"):raise ValidationError("Unsupported payment method")
  obj=serializer.save(reference="AGP-"+uuid.uuid4().hex[:12].upper(),received_by=self.request.user,status="pending",paid_at=timezone.now())
  log(self.request.user,"payment.recorded_pending",obj)
 @action(detail=True,methods=["post"])
 def confirm(self,request,pk=None):
  check_role(request.user,"Administrator")
  with transaction.atomic():
   obj=Payment.objects.select_for_update().get(pk=pk)
   if obj.status!="pending":raise ValidationError("Only pending payments can be confirmed")
   obj.status="confirmed";obj.save(update_fields=["status"]);log(request.user,"payment.confirmed",obj)
  return Response(self.get_serializer(obj).data)
class StaffViewSet(viewsets.ReadOnlyModelViewSet):
 queryset=StaffUser.objects.all().order_by("name")
 serializer_class=StaffSerializer
 def get_queryset(self):
  check_role(self.request.user,"Administrator")
  return super().get_queryset()
@api_view(["GET"])
def me(request):
 return Response(StaffSerializer(request.user).data)
@api_view(["GET"])
def summary(request):
 check_role(request.user,"Administrator","Supervisor","Revenue Officer")
 return Response({"facility_count":Facility.objects.count(),"contracted_monthly":Facility.objects.aggregate(total=Sum("monthly_fee"))["total"] or 0,"collections":list(Collection.objects.values("status").annotate(total=Count("id"))),"payments_received":Payment.objects.filter(status="confirmed").aggregate(total=Sum("amount"))["total"] or 0,"currency":"UGX"})

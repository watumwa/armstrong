from rest_framework import serializers
from .models import Facility,Agreement,Collection,Payment,StaffUser
class FacilitySerializer(serializers.ModelSerializer):
 class Meta:
  model=Facility
  fields=["id","code","name","type","address","district","phone","latitude","longitude","monthly_fee","collection_day","created_at"]
  read_only_fields=["id","code","created_at"]
 def validate(self,attrs):
  lat=attrs.get("latitude",getattr(self.instance,"latitude",None));lon=attrs.get("longitude",getattr(self.instance,"longitude",None))
  if (lat is None)!=(lon is None):raise serializers.ValidationError("Provide both latitude and longitude or neither.")
  if lat is not None and not -90<=lat<=90:raise serializers.ValidationError("Invalid latitude")
  if lon is not None and not -180<=lon<=180:raise serializers.ValidationError("Invalid longitude")
  return attrs
class StaffSerializer(serializers.ModelSerializer):
 class Meta:
  model=StaffUser
  fields=["id","name","email","role","active","created_at"]
  read_only_fields=["id","created_at"]
class AgreementSerializer(serializers.ModelSerializer):
 class Meta:
  model=Agreement
  fields="__all__"
  read_only_fields=["id","reference","created_at"]
class CollectionSerializer(serializers.ModelSerializer):
 class Meta:
  model=Collection
  fields="__all__"
  read_only_fields=["id","verified_by","verified_at","created_at"]
class PaymentSerializer(serializers.ModelSerializer):
 class Meta:
  model=Payment
  fields="__all__"
  read_only_fields=["id","reference","received_by","status","paid_at","created_at"]

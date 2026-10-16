from django.urls import path,include
from rest_framework.routers import DefaultRouter
from .views import FacilityViewSet,AgreementViewSet,CollectionViewSet,PaymentViewSet,StaffViewSet,me,summary
router=DefaultRouter()
router.register("facilities",FacilityViewSet)
router.register("agreements",AgreementViewSet)
router.register("collections",CollectionViewSet,basename="collections")
router.register("payments",PaymentViewSet,basename="payments")
router.register("users",StaffViewSet)
urlpatterns=[path("v1/auth/me/",me),path("v1/reports/summary/",summary),path("v1/",include(router.urls))]

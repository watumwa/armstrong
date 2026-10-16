from django.urls import include, path

urlpatterns = [
    path("api/", include("operations.api_urls")),
    path("", include("operations.urls")),
]

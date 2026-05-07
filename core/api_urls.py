from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import DeviceViewSet, ProjectViewSet

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"devices", DeviceViewSet, basename="device")

urlpatterns = [
    path("", include(router.urls)),
]


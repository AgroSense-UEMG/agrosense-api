from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Importando as views, incluindo a nossa nova UserRegistrationView
from .views import DeviceViewSet, ProjectViewSet, UserRegistrationView

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"devices", DeviceViewSet, basename="device")

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    
    path("", include(router.urls)),
]

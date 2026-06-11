from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import (
    DeviceRegistrationView, 
    TelemetryIngestionView, 
    DeviceViewSet, 
    ProjectViewSet, 
    UserRegistrationView
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"devices", DeviceViewSet, basename="device")

urlpatterns = [
    # ROTAS DO HARDWARE
    path('hw/register/', DeviceRegistrationView.as_view(), name='device-register'),
    path('hw/data/', TelemetryIngestionView.as_view(), name='hw-telemetry'),
    # ROTA DE USUÁRIO
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    # ROTAS AUTOMÁTICAS DA INTERFACE WEB
    path("", include(router.urls)),
]
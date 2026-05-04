from django.urls import path
from .views import DeviceRegistrationView, TelemetryIngestionView

urlpatterns = [
    # Quando o ESP32 acessar "hw/register/", ele cai na lógica de registro
    path('hw/register/', DeviceRegistrationView.as_view(), name='device-register'),
    path('hw/data/', TelemetryIngestionView.as_view(), name='hw-telemetry'),
]
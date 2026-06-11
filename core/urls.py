from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DeviceViewSet, 
    ProjectInviteCreateView, 
    ProjectInviteAcceptView, 
    DeviceReadingsView
)

router = DefaultRouter()
router.register(r'devices', DeviceViewSet, basename='device')

urlpatterns = [
    path('', include(router.urls)),
    
    # Rotas de Convite do Lucas
    path('projects/<uuid:project_id>/invite/', ProjectInviteCreateView.as_view(), name='project-invite-create'),
    path('invites/accept/', ProjectInviteAcceptView.as_view(), name='project-invite-accept'),
    
    # Rota de Leituras (adaptada para usar o nome do dispositivo do nosso Front-end)
    path('devices/<str:device_name>/readings/', DeviceReadingsView.as_view(), name='device-readings'),
]
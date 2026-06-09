from django.urls import include, path
from rest_framework.routers import DefaultRouter

# Importando as views, incluindo a nossa nova UserRegistrationView
from .views import (
    DeviceReadingsView,
    DeviceViewSet,
    ProjectInviteAcceptView,
    ProjectInviteListView,
    ProjectInviteView,
    ProjectViewSet,
    UserRegistrationView,
)

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"devices", DeviceViewSet, basename="device")

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("devices/<int:id>/readings/", DeviceReadingsView.as_view(), name="device-readings"),
    path("projects/<int:project_pk>/invite/", ProjectInviteView.as_view(), name="project-invite"),
    path("invites/", ProjectInviteListView.as_view(), name="project-invite-list"),
    path("invites/accept/", ProjectInviteAcceptView.as_view(), name="project-invite-accept"),
    
    path("", include(router.urls)),
]

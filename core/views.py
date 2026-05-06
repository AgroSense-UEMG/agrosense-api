from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Project
from .serializers import ProjectSerializer


class ProjectViewSet(ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

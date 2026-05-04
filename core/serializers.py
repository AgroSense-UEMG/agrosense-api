from rest_framework import serializers

from .models import Device, Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "created_at"]
        read_only_fields = ["id", "created_at"]


class DeviceSerializer(serializers.ModelSerializer):
    project_id = serializers.PrimaryKeyRelatedField(
        source="project",
        queryset=Project.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    project = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Device
        fields = ["id", "name", "project", "project_id", "is_online", "created_at"]
        read_only_fields = ["id", "project", "is_online", "created_at"]

    def validate_project_id(self, project: Project | None):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        if project is None:
            return project

        if user is None or not user.is_authenticated:
            raise serializers.ValidationError("Authentication required.")

        if project.user_id != user.id:
            raise serializers.ValidationError("You cannot link a device to this project.")

        return project


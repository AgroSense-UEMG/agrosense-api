from datetime import datetime, time

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny 
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model 

from .models import Device, Measurement, Project, ProjectInvite
from .serializers import (
    DeviceRegistrationSerializer, 
    MeasurementSerializer,
    MeasurementHistorySerializer,
    ProjectInviteSerializer,
    ProjectSerializer, 
    DeviceSerializer,
    UserRegistrationSerializer 
)


User = get_user_model()


def visible_devices_for(user):
    return Device.objects.filter(
        Q(user=user) | Q(project__user=user) | Q(project__members=user)
    ).distinct()


class MeasurementHistoryPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 500


class DeviceRegistrationView(APIView):
    # Garante que apenas usuários com Token válido tenham acesso
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Transfere os dados que vieram do ESP32 para o tradutor
        serializer = DeviceRegistrationSerializer(data=request.data)
        
        # O Django convoca a função 'validate_manifest' do serializers.py
        if serializer.is_valid():

            # Se estiver tudo certo, salva no banco
            # 'owner=request.user' preenche o dono do dispositivo usando o Token
            serializer.save(user=request.user)

            return Response(
                {"message": "Dispositivo registrado com sucesso!", "name": serializer.data.get('name')}, 
                status=status.HTTP_201_CREATED
            )
        
        # Se o JSON estiver errado, retorna o erro 400
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TelemetryIngestionView(generics.CreateAPIView):
    queryset = Measurement.objects.all()
    serializer_class = MeasurementSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # O Serializer limpa e valida os dados brutos da requisição
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Coleta os dados que o hardware enviou
            validated_data = serializer.validated_data

            # Extrai o nome para buscar o dispositivo
            device_name = validated_data.pop('name') # O .pop() remove o 'name' da lista
            
            # Busca o objeto Device real no banco para fazer o vínculo (FK)
            device = Device.objects.filter(name=device_name, user=request.user).first()
            
            if not device:
                return Response({"error": "Dispositivo não encontrado."}, status=status.HTTP_404_NOT_FOUND)

            serializer.save(device=device, **validated_data)
            device.is_online = True
            device.last_seen = timezone.now()
            device.save(update_fields=["is_online", "last_seen"])
            
            return Response(
                {"status": "success", "message": "Telemetria salva!"}, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeviceReadingsView(generics.ListAPIView):
    serializer_class = MeasurementHistorySerializer
    permission_classes = [IsAuthenticated]
    pagination_class = MeasurementHistoryPagination

    def _parse_iso_datetime(self, value, field_name, is_end_date=False):
        try:
            parsed = parse_datetime(value)

            if parsed is None:
                parsed_date = parse_date(value)
                if parsed_date is None:
                    raise ValidationError({field_name: "Formato inválido. Use uma data em formato ISO."})

                parsed = datetime.combine(parsed_date, time.max if is_end_date else time.min)
        except ValueError:
            raise ValidationError({field_name: "Formato inválido. Use uma data em formato ISO."})

        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())

        return parsed

    def get_queryset(self):
        device = generics.get_object_or_404(
            visible_devices_for(self.request.user),
            id=self.kwargs.get("id"),
        )
        queryset = Measurement.objects.filter(device=device).order_by("-timestamp")

        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")

        if start_date:
            queryset = queryset.filter(
                timestamp__gte=self._parse_iso_datetime(start_date, "start_date")
            )

        if end_date:
            queryset = queryset.filter(
                timestamp__lte=self._parse_iso_datetime(end_date, "end_date", is_end_date=True)
            )

        return queryset


class ProjectViewSet(ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = Project.objects.filter(
            Q(user=self.request.user) | Q(members=self.request.user)
        ).distinct()

        if self.action in ["update", "partial_update", "destroy"]:
            queryset = queryset.filter(user=self.request.user)

        return queryset.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ProjectInviteView(generics.CreateAPIView):
    serializer_class = ProjectInviteSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        project = generics.get_object_or_404(
            Project,
            pk=self.kwargs.get("project_pk"),
            user=self.request.user,
        )
        email = serializer.validated_data["email"]

        if email.lower() == self.request.user.email.lower():
            raise ValidationError({"email": "Você não pode convidar a si mesmo."})

        if project.members.filter(email__iexact=email).exists():
            raise ValidationError({"email": "Este usuário já é membro do projeto."})

        if ProjectInvite.objects.filter(
            project=project,
            email__iexact=email,
            status=ProjectInvite.STATUS_PENDING,
        ).exists():
            raise ValidationError({"email": "Já existe um convite pendente para este e-mail."})

        invite = serializer.save(project=project, invited_by=self.request.user)
        accept_url = f"/api/invites/accept/"

        send_mail(
            subject=f"Convite para o projeto {project.name}",
            message=(
                f"Você foi convidado para participar do projeto {project.name} no AgroSense.\n\n"
                f"Use este token para aceitar o convite: {invite.token}\n"
                f"Endpoint de aceite: {accept_url}"
            ),
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@agrosense.local"),
            recipient_list=[invite.email],
            fail_silently=False,
        )


class ProjectInviteListView(generics.ListAPIView):
    serializer_class = ProjectInviteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProjectInvite.objects.filter(
            email__iexact=self.request.user.email,
            status=ProjectInvite.STATUS_PENDING,
        ).order_by("-created_at")


class ProjectInviteAcceptView(generics.GenericAPIView):
    serializer_class = ProjectInviteSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        token = request.data.get("token")

        if not token:
            return Response(
                {"error": "Token é obrigatório."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invite = generics.get_object_or_404(
            ProjectInvite,
            token=token,
            email__iexact=request.user.email,
            status=ProjectInvite.STATUS_PENDING,
        )
        invite.status = ProjectInvite.STATUS_ACCEPTED
        invite.accepted_at = timezone.now()
        invite.save(update_fields=["status", "accepted_at"])
        invite.project.members.add(request.user)

        serializer = self.get_serializer(invite)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeviceViewSet(ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        if self.action == "partial_update":
            return Device.objects.filter(user=self.request.user).order_by("-created_at")

        return visible_devices_for(self.request.user).order_by("-created_at")

    @action(detail=True, methods=["get"], url_path="manifest")
    def manifest(self, request, pk=None):
        device = self.get_object()
        return Response({"manifest": device.manifest})


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    # AllowAny é fundamental aqui: permite que um usuário sem conta acesse essa rota para criar uma!
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

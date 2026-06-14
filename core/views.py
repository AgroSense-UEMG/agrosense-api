from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny 
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from django.contrib.auth import get_user_model 

from .models import Device, Measurement, Project, ProjectMember
from .serializers import (
    DeviceRegistrationSerializer, 
    MeasurementSerializer,
    ProjectSerializer, 
    DeviceSerializer,
    UserRegistrationSerializer,
    MemberSerializer,
    InviteMemberSerializer,
)


User = get_user_model()


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
            
            return Response(
                {"status": "success", "message": "Telemetria salva!"}, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ProjectViewSet(ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # ─── Membros ─────────────────────────────────────────────

    @action(detail=True, methods=["get"], url_path="members")
    def members(self, request, pk=None):
        project = self.get_object()
        members_qs = ProjectMember.objects.filter(project=project).select_related("user")
        serializer = MemberSerializer(members_qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="invite")
    def invite(self, request, pk=None):
        project = self.get_object()
        invite_serializer = InviteMemberSerializer(data=request.data)
        invite_serializer.is_valid(raise_exception=True)
        email = invite_serializer.validated_data["email"]

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {"error": "Usuário não encontrado. O convidado precisa ter uma conta na plataforma."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if ProjectMember.objects.filter(project=project, user=user).exists():
            return Response(
                {"error": "Este usuário já é membro do projeto."},
                status=status.HTTP_409_CONFLICT,
            )

        member = ProjectMember.objects.create(project=project, user=user, role="Pesquisador")
        return Response(
            MemberSerializer(member).data,
            status=status.HTTP_201_CREATED,
        )

    # ─── Devices do projeto ──────────────────────────────────

    @action(detail=True, methods=["get"], url_path="devices")
    def project_devices(self, request, pk=None):
        project = self.get_object()
        devices = Device.objects.filter(project=project)
        serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class DeviceViewSet(ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [IsAuthenticated]

    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        return Device.objects.filter(user=self.request.user).order_by("-created_at")

    # Endpoint de manifesto
    @action(detail=True, methods=["get"], url_path="manifest")
    def manifest(self, request, pk=None):
        # O self.get_object() busca o dispositivo pelo ID (pk) da URL
        device = self.get_object()
        return Response(device.manifest, status=status.HTTP_200_OK)
    
    # Endpoint de hiostórico
    @action(detail=True, methods=["get"], url_path="readings")
    def readings(self, request, pk=None):
        device = self.get_object()
        measurements = device.measurements.all()

        # Captura os filtros 'start_date' e 'end_date' enviados na URL pelo front-end
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Aplica os filtros se eles existirem na requisição
        if start_date:
            measurements = measurements.filter(timestamp__gte=start_date)
        if end_date:
            measurements = measurements.filter(timestamp__lte=end_date)
            
        # Retorna uma lista de dicionários contendo apenas 'timestamp' e o JSON 'data'
        history_data = measurements.values('timestamp', 'data')
        
        return Response(history_data, status=status.HTTP_200_OK)

class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    # AllowAny é fundamental aqui: permite que um usuário sem conta acesse essa rota para criar uma!
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

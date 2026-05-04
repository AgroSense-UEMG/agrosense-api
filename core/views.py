from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated
from .models import Device, Measurement
from .serializers import DeviceRegistrationSerializer, MeasurementSerializer

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

    def create(self, request, *args, **kwargs):
        # O Serializer limpa e valida os dados brutos da requisição
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Coleta os dados que o hardware enviou
            validated_data = serializer.validated_data

            # Extrai o nome para buscar o dispositivo
            device_name = validated_data.pop('name') # O .pop() remove o 'name' da lista
            
            # Busca o objeto Device real no banco para fazer o vínculo (FK)
            device = Device.objects.filter(name=device_name).first()
            
            if not device:
                return Response({"error": "Dispositivo não encontrado."}, status=status.HTTP_404_NOT_FOUND)

            serializer.save(device=device, **validated_data)
            
            return Response(
                {"status": "success", "message": "Telemetria salva!"}, 
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
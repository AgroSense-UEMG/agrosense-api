from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .serializers import DeviceRegistrationSerializer

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

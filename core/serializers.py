from rest_framework import serializers
from .models import Device, Measurement

class DeviceRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        # O hardware envia apenas esses dois campos
        fields = ['name', 'manifest']
        
    def validate_manifest(self, value):
        # Garante que o manifest enviado seja um JSON válido
        if not isinstance(value, dict):
            raise serializers.ValidationError("O manifesto deve ser um objeto JSON válido.")
        
        # Define quais chaves são obrigatórias dentro do JSON
        required_keys = ['name', 'components']

        # Se faltar qualquer um dos campos, retorna um erro 400
        for key in required_keys:
            if key not in value:
                raise serializers.ValidationError(f"O campo '{key}' está faltando no manifesto.")
                
        return value

class MeasurementSerializer(serializers.ModelSerializer):
    # Usamos o 'name' para identificar o hardware no JSON enviado
    name = serializers.CharField(write_only=True)

    class Meta:
        model = Measurement
        fields = ['name', 'data'] # 'data' receberá o payload com as leituras dos sensores

    def validate_name(self, value):
        # Validação Crítica: verifica se o hardware_id (name) existe no sistema
        if not Device.objects.filter(name=value).exists():
            raise serializers.ValidationError("Dispositivo não encontrado ou não registrado.")
        return value
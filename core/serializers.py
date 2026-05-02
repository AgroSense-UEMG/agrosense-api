from rest_framework import serializers
from .models import Device

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
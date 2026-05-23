from rest_framework import serializers
from django.contrib.auth import get_user_model  
from .models import Device, Measurement, Project
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed

User = get_user_model()

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
    # Usa o 'name' para identificar o hardware no JSON enviado
    name = serializers.CharField(write_only=True)

    class Meta:
        model = Measurement
        fields = ['name', 'data'] # 'data' receberá o payload com as leituras dos sensores

    def validate_name(self, value):
        # Validação Crítica: verifica se o hardware_id (name) existe no sistema
        if not Device.objects.filter(name=value).exists():
            raise serializers.ValidationError("Dispositivo não encontrado ou não registrado.")
        return value

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

class UserRegistrationSerializer(serializers.ModelSerializer):
    # write_only=True garante que a senha não vaze nas respostas da API
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'password')

    def create(self, validated_data):
        # 1. Extraí o e-mail que veio do Front-end
        email = validated_data['email']
        
        # 2. GERA O USERNAME: Pegamos tudo antes do '@'
        username_gerado = email.split('@')[0]
        
        # 3. Passa o username obrigatório para o create_user
        user = User.objects.create_user(
            username=username_gerado, 
            email=email,
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'] = serializers.EmailField()
        # Remove a obrigatoriedade do 'username' padrão
        del self.fields['username']

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        # 1. Busca o usuário no banco pelo e-mail
        user = User.objects.filter(email=email).first()

        # 2. Se o usuário existir e a senha estiver certa:
        if user and user.check_password(password):
            refresh = self.get_token(user)
            return {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'id': user.id,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            }

        # 3. Se errar e-mail ou senha, devolve o Erro 401 (Não Autorizado)
        raise AuthenticationFailed('E-mail ou senha incorretos.', code='authorization')
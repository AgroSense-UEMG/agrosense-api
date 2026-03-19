from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class InstitutionalDomain(models.Model):
    
    domain = models.CharField(max_length=255, unique=True) # Domain of the institution example: @uemg.br
    description = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.domain

from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    # Add custom fields here if needed in the future
    
    def save(self, *args, **kwargs):
        if self.email:
            domain = self.email.split('@')[-1]
            if not InstitutionalDomain.objects.filter(domain=domain).exists():
                # Allow superusers to bypass this check (optional, but good for safety)
                if not self.is_superuser:
                    raise ValidationError(f"The domain @{domain} is not allowed.")
        super().save(*args, **kwargs)

# --- Main models ---

class TimeStampedModel(models.Model):
    # Essa classe adiciona campos de data automaticamente. (Princípio DRY - Don't Repeat Yourself).
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Criado em")

    class Meta:
        abstract = True # Essa classe não vira uma tabela, apenas fornece campos para as outras

class Project(TimeStampedModel):
    # Serve para agrupar os dispositivos do usuário
    name = models.CharField(max_length=255, verbose_name="Nome do Projeto")
    description = models.TextField(blank=True, null=True, verbose_name="Descrição")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='projects', verbose_name="Responsável")

    class Meta:
        # Uso de verbose_name apenas para traduzir os campos principais no painel de administração
        verbose_name = "Projeto"
        verbose_name_plural = "Projetos"

    def __str__(self):
        return self.name

class Device(TimeStampedModel):
    '''
    Classe que representa o dispostivo físico
    O 'manifest' guarda quais sensores um dispositivo específico possui
    '''
    name = models.CharField(max_length=255, verbose_name="Nome do Dispositivo")
    # Esse campo guarda o JSON com as configurações do hardware
    manifest = models.JSONField(default=dict, verbose_name="Configuração (JSON)")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='devices', null=True, blank=True, verbose_name="Projeto")
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='devices', verbose_name="Proprietário")
    is_online = models.BooleanField(default=False, verbose_name="Status Online")

    class Meta:
        verbose_name = "Dispositivo"
        verbose_name_plural = "Dispositivos"

    def __str__(self):
        return self.name

class Measurement(models.Model):
    # Guarda cada leitura enviada pelos sensores de temperatura, umidade, etc.
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='measurements', verbose_name="Dispositivo de Origem")
    data = models.JSONField(verbose_name="Dados da Leitura") 
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Horário da Coleta")

    class Meta:
        verbose_name = "Medição"
        verbose_name_plural = "Medições"
        ordering = ['-timestamp']
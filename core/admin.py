from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, InstitutionalDomain, Project, Device, Measurement

# Registra o usuário personalizado usando o padrão do Django (UserAdmin)
admin.site.register(CustomUser, UserAdmin)
# Registra os domínios permitidos (ex: @uemg.br)
admin.site.register(InstitutionalDomain)

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    # Define quais colunas aparecem na tabela de listagem de projetos
    list_display = ('name', 'user')
    # Adiciona uma barra de pesquisa para buscar projetos pelo nome
    search_fields = ('name',)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    # Colunas: Nome do aparelho, quem é o dono, a qual projeto pertence e se está online
    list_display = ('name', 'user', 'project', 'is_online')
    # Cria filtros na lateral direita para facilitar a navegação
    list_filter = ('is_online', 'project')
    # Permite pesquisar pelo nome do dispositivo
    search_fields = ('name',)

@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    # Exibe qual dispositivo enviou o dado e em qual horário
    list_display = ('device', 'timestamp')
    # Define que o horário não pode ser editado manualmente, apenas visualizado
    readonly_fields = ('timestamp',)
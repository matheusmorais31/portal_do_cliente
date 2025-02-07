# clientes/admin.py

from django.contrib import admin
from .models import ClienteProfile

@admin.register(ClienteProfile)
class ClienteProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'cnpj_cpf', 'razao_social', 'nome_fantasia', 'filial')
    search_fields = ('cnpj_cpf', 'razao_social', 'nome_fantasia')

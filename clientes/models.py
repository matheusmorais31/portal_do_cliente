# models.py
from django.db import models
from django.conf import settings  # Para acessar AUTH_USER_MODEL

class ClienteProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    cnpj_cpf = models.CharField(max_length=20, unique=True)
    razao_social = models.CharField(max_length=255)
    nome_fantasia = models.CharField(max_length=255, blank=True, null=True)
    filial = models.CharField(max_length=50, blank=True, null=True)
    rua = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=50, blank=True, null=True)
    bairro = models.CharField(max_length=255, blank=True, null=True)
    cidade = models.CharField(max_length=255, blank=True, null=True)
    uf = models.CharField(max_length=2, blank=True, null=True)
    codigo_cliente = models.CharField(max_length=50, unique=True)
    tipo_cliente = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.razao_social} ({self.cnpj_cpf})"


class Classificacao(models.Model):
    cliente = models.ForeignKey(
        ClienteProfile,
        on_delete=models.CASCADE,
        related_name="classificacoes"
    )
    nome = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nome} ({self.cliente.razao_social})"

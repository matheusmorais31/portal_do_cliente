from django.core.management.base import BaseCommand
from clientes.models import ClienteProfile, Classificacao
from clientes.utils import get_firebird_connection
from django.db import transaction
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Atualiza todos os dados dos clientes já importados, incluindo classificações"

    def handle(self, *args, **kwargs):
        try:
            conn = get_firebird_connection()
            cursor = conn.cursor()

            # Busca os dados no Firebird
            sql = """
            SELECT 
                CLIFOREND.CGC AS CNPJ_CPF,
                CLIFOREND.CCLIFOR AS CODIGO_CLIENTE,
                CLIFOREND.NOMEFILIAL AS RAZAO_SOCIAL,
                CLIFOREND.FANTASIA AS NOME_FANTASIA,
                CLIFOREND.FILIALCF AS FILIAL,
                CLIFOREND.ENDERECO AS RUA,
                CLIFOREND.NUMERO,
                CLIFOREND.BAIRRO,
                CIDADE.CIDADE,
                CIDADE.UF,
                CLASSIFICACAO.CLASSIFICACAO
            FROM CLIFOREND
            JOIN CIDADE ON CLIFOREND.CCIDADE = CIDADE.CCIDADE
            JOIN CLIFORCLAS ON CLIFOREND.CCLIFOR = CLIFORCLAS.CCLIFOR
            JOIN CLASSIFICACAO ON CLIFORCLAS.CCLASSIFICACAO = CLASSIFICACAO.CCLASSIFICACAO
            WHERE CLIFOREND.ATIVO = 'S'
            """
            cursor.execute(sql)
            clientes = cursor.fetchall()

            colunas = [desc[0] for desc in cursor.description]

            # Organiza os dados retornados
            cliente_data = {}
            for cliente in clientes:
                dados = dict(zip(colunas, cliente))
                cnpj_cpf = dados["CNPJ_CPF"]

                if cnpj_cpf not in cliente_data:
                    cliente_data[cnpj_cpf] = {
                        "CODIGO_CLIENTE": dados["CODIGO_CLIENTE"],
                        "RAZAO_SOCIAL": dados["RAZAO_SOCIAL"],
                        "NOME_FANTASIA": dados.get("NOME_FANTASIA"),
                        "FILIAL": dados.get("FILIAL"),
                        "RUA": dados.get("RUA"),
                        "NUMERO": dados.get("NUMERO"),
                        "BAIRRO": dados.get("BAIRRO"),
                        "CIDADE": dados.get("CIDADE"),
                        "UF": dados.get("UF"),
                        "CLASSIFICACOES": set(),
                    }
                cliente_data[cnpj_cpf]["CLASSIFICACOES"].add(dados["CLASSIFICACAO"])

            # Atualiza os registros no banco de dados Django
            total_atualizados = 0
            with transaction.atomic():
                for cliente in ClienteProfile.objects.all():
                    cnpj_cpf = cliente.cnpj_cpf
                    dados = cliente_data.get(cnpj_cpf)

                    if dados:
                        # Atualiza os dados do cliente
                        cliente.codigo_cliente = dados["CODIGO_CLIENTE"]
                        cliente.razao_social = dados["RAZAO_SOCIAL"]
                        cliente.nome_fantasia = dados["NOME_FANTASIA"]
                        cliente.filial = dados["FILIAL"]
                        cliente.rua = dados["RUA"]
                        cliente.numero = dados["NUMERO"]
                        cliente.bairro = dados["BAIRRO"]
                        cliente.cidade = dados["CIDADE"]
                        cliente.uf = dados["UF"]
                        cliente.save()

                        # Atualiza as classificações
                        cliente.classificacoes.all().delete()  # Remove classificações antigas
                        Classificacao.objects.bulk_create(
                            [Classificacao(cliente=cliente, nome=classificacao) for classificacao in dados["CLASSIFICACOES"]]
                        )

                        total_atualizados += 1

            logger.info(f"{total_atualizados} clientes atualizados com sucesso.")
            self.stdout.write(self.style.SUCCESS(f"{total_atualizados} clientes atualizados com sucesso."))

        except Exception as e:
            logger.error(f"Erro ao atualizar os dados dos clientes: {e}")
            self.stderr.write(self.style.ERROR(f"Erro ao atualizar os dados dos clientes: {e}"))

import logging
import sys
import fdb
import xmltodict
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.db import transaction
from .models import ClienteProfile, Classificacao
from .firebird_config import FIREBIRD_SETTINGS
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)
User = get_user_model()


def conectar_firebird():
    """Estabelece conexão com o banco Firebird e retorna a conexão."""
    logger.info("Tentando conectar ao banco Firebird.")
    try:
        conn = fdb.connect(
            host=FIREBIRD_SETTINGS['host'],
            database=FIREBIRD_SETTINGS['database'],
            user=FIREBIRD_SETTINGS['user'],
            password=FIREBIRD_SETTINGS['password'],
            port=FIREBIRD_SETTINGS['port']
        )
        logger.info("Conexão com o Firebird estabelecida com sucesso.")
        return conn
    except fdb.Error as e:
        logger.error(f"Erro ao conectar ao Firebird: {e}")
        return None


def get_firebird_connection():
    """Estabelece conexão com o banco Firebird."""
    logger.info("Tentando conectar ao banco Firebird.")
    try:
        conn = fdb.connect(
            host=FIREBIRD_SETTINGS['host'],
            database=FIREBIRD_SETTINGS['database'],
            user=FIREBIRD_SETTINGS['user'],
            password=FIREBIRD_SETTINGS['password'],
            port=FIREBIRD_SETTINGS['port']
        )
        logger.info("Conexão com o Firebird estabelecida com sucesso.")
        return conn
    except fdb.Error as e:
        logger.error(f"Erro ao conectar ao Firebird: {e}")
        raise


def listar_clientes_disponiveis():
    """
    Lista os clientes disponíveis para importação, agrupando classificações por CNPJ/CPF.
    """
    logger.info("Executando consulta para listar clientes disponíveis.")
    try:
        conn = get_firebird_connection()
        cursor = conn.cursor()

        sql = """
        SELECT  
            CLIFOREND.CGC AS CNPJ_CPF,
            CLIFOREND.NOMEFILIAL AS RAZAO_SOCIAL,
            CLASSIFICACAO.CLASSIFICACAO
        FROM CLIFOREND
        JOIN CLIFORCLAS ON CLIFOREND.CCLIFOR = CLIFORCLAS.CCLIFOR
        JOIN CLASSIFICACAO ON CLIFORCLAS.CCLASSIFICACAO = CLASSIFICACAO.CCLASSIFICACAO
        WHERE CLIFOREND.ATIVO = 'S'
          AND CLASSIFICACAO.CCLASSIFICACAO IN ('17','24','31')
        """
        cursor.execute(sql)
        clientes = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]

        grouped_clientes = defaultdict(lambda: {"CNPJ_CPF": "", "RAZAO_SOCIAL": "", "CLASSIFICACAO": ""})
        for cliente in clientes:
            dados = dict(zip(colunas, cliente))
            cnpj_cpf = dados["CNPJ_CPF"]
            grouped_clientes[cnpj_cpf]["CNPJ_CPF"] = dados["CNPJ_CPF"]
            grouped_clientes[cnpj_cpf]["RAZAO_SOCIAL"] = dados["RAZAO_SOCIAL"]
            if dados.get("CLASSIFICACAO"):
                if grouped_clientes[cnpj_cpf]["CLASSIFICACAO"]:
                    grouped_clientes[cnpj_cpf]["CLASSIFICACAO"] += f", {dados['CLASSIFICACAO']}"
                else:
                    grouped_clientes[cnpj_cpf]["CLASSIFICACAO"] = dados["CLASSIFICACAO"]

        result = list(grouped_clientes.values())
        logger.info(f"Clientes listados com sucesso: {len(result)} clientes encontrados.")
        cursor.close()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"Erro ao listar clientes: {e}", exc_info=True)
        return []


def importar_clientes(clientes_selecionados):
    logger.info("Iniciando processo de importação de clientes.")
    try:
        conn = get_firebird_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(clientes_selecionados))
        sql = f"""
        SELECT  
            CLIFOREND.CGC AS CNPJ_CPF,
            CLIFOREND.NOMEFILIAL AS RAZAO_SOCIAL,
            CLASSIFICACAO.CLASSIFICACAO,
            CLIFOREND.FANTASIA AS NOME_FANTASIA,
            CLIFOREND.FILIALCF AS FILIAL,
            CLIFOREND.ENDERECO AS RUA,
            CLIFOREND.NUMERO,
            CLIFOREND.BAIRRO,
            CIDADE.CIDADE,
            CIDADE.UF,
            CLIFOREND.ATIVO,
            CLIFOREND.CCLIFOR AS CODIGO_CLIENTE 
        FROM CLIFOREND
        JOIN CIDADE ON CLIFOREND.CCIDADE = CIDADE.CCIDADE 
        JOIN CLIFORCLAS ON CLIFOREND.CCLIFOR = CLIFORCLAS.CCLIFOR 
        JOIN CLASSIFICACAO ON CLIFORCLAS.CCLASSIFICACAO = CLASSIFICACAO.CCLASSIFICACAO 
        WHERE CLIFOREND.ATIVO = 'S' 
          AND CLIFOREND.CGC IN ({placeholders}) 
          AND CLASSIFICACAO.CCLASSIFICACAO IN ('17', '24', '31')
        """
        cursor.execute(sql, clientes_selecionados)
        rows = cursor.fetchall()
        colunas = [desc[0] for desc in cursor.description]
        dados_agrupados = defaultdict(list)
        for row in rows:
            row_dict = dict(zip(colunas, row))
            cnpj_cpf = row_dict['CNPJ_CPF']
            dados_agrupados[cnpj_cpf].append(row_dict)
        total_importados = 0
        with transaction.atomic():
            for cnpj_cpf, linhas_cliente in dados_agrupados.items():
                classificacoes_encontradas = {linha['CLASSIFICACAO'] for linha in linhas_cliente}
                if '17' in classificacoes_encontradas:
                    tipo_cliente = '17'
                else:
                    tipo_cliente = '24/31' if ('24' in classificacoes_encontradas or '31' in classificacoes_encontradas) else 'Indefinido'
                linha_principal = linhas_cliente[0]
                razao_social = linha_principal['RAZAO_SOCIAL']
                nome_fantasia = linha_principal.get('NOME_FANTASIA')
                filial = linha_principal.get('FILIAL')
                rua = linha_principal.get('RUA')
                numero = linha_principal.get('NUMERO')
                bairro = linha_principal.get('BAIRRO')
                cidade = linha_principal.get('CIDADE')
                uf = linha_principal.get('UF')
                codigo_cliente = linha_principal.get('CODIGO_CLIENTE')
                username = cnpj_cpf.replace('.', '').replace('/', '').replace('-', '')
                email = f"{username}@empresa.com"
                user, created = User.objects.get_or_create(
                    username=username,
                    defaults={'email': email, 'first_name': razao_social, 'is_active': True}
                )
                if created:
                    random_password = get_random_string(length=12)
                    user.set_password(random_password)
                    user.save()
                cliente_profile, _ = ClienteProfile.objects.update_or_create(
                    user=user,
                    defaults={
                        'cnpj_cpf': cnpj_cpf,
                        'razao_social': razao_social,
                        'nome_fantasia': nome_fantasia,
                        'filial': filial,
                        'rua': rua,
                        'numero': numero,
                        'bairro': bairro,
                        'cidade': cidade,
                        'uf': uf,
                        'codigo_cliente': codigo_cliente,
                        'tipo_cliente': tipo_cliente,
                    }
                )
                for classificacao in classificacoes_encontradas:
                    Classificacao.objects.get_or_create(cliente=cliente_profile, nome=classificacao)
                total_importados += 1
        logger.info(f"Total de clientes importados: {total_importados}")
        cursor.close()
        conn.close()
        return total_importados
    except Exception as e:
        logger.error(f"Erro ao importar clientes: {e}", exc_info=True)
        return 0


def listar_pedidos_do_cliente(codigo_cliente):
    """
    Retorna todos os pedidos do cliente (PEDIDO.CCLIFOR) no Firebird utilizando a query atualizada.
    A query relaciona o campo NFSAIDA.NFS (alias SEQUENCIAL_TECNICON) com CHAVENFE.NFS e inclui
    os dados dos endereços (principal e alternativo).
    """
    logger.info(f"Buscando pedidos do cliente (CCLIFOR) = {codigo_cliente} no Firebird.")
    try:
        conn = get_firebird_connection()
        cursor = conn.cursor()
        query = """
        WITH VT AS (
            SELECT 
                PEDIDO.CFILIAL, 
                PEDIDO."DATA" AS DT_INCLUSAO,
                PEDIDO.PEDIDO,
                PEDIDO.CREVENDA AS COD_REVENDA,
                REVENDA.NOME AS REVENDA,
                PEDIDO.CVENDEDOR, 
                PEDIDO.CCLIFOR AS COD_CLIENTE,
                PEDIDO.PREVDT AS DATA_ENTREGA,
                CLIFOR.NOME AS NOME_CLIENTE,
                PEDIDO.FILIALCF,
                -- Endereço alternativo (único, via subconsulta)
                CLIFOREND_UNICO.ENDERECO AS ENDERECO_ALTERNATIVO,
                CLIFOREND_UNICO.NUMERO AS NUMERO_ALTERNATIVO,
                CLIFOREND_UNICO.CCIDADE AS COD_CIDADE_ALTERNATIVO,
                CIDADE_ALT.CIDADE AS CIDADE_ALTERNATIVO,
                CIDADE_ALT.UF AS UF_ALTERNATIVO,
                -- Endereço principal
                CLIENDENT.ENDERECO AS ENDERECO_PRINCIPAL,
                CLIENDENT.NUMERO AS NUMERO_PRINCIPAL,
                CLIENDENT.CCIDADE AS COD_CIDADE_PRINCIPAL,
                CIDADEPRIN.CIDADE AS CIDADE_PRINCIPAL,
                CIDADEPRIN.UF AS UF_PRINCIPAL,
                -- Endereço de entrega final (usa o principal se existir; senão, o alternativo)
                COALESCE(CLIENDENT.ENDERECO, CLIFOREND_UNICO.ENDERECO) AS ENDERECO_ENTREGA,
                COALESCE(CLIENDENT.NUMERO, CLIFOREND_UNICO.NUMERO) AS NUMERO_ENTREGA,
                COALESCE(CIDADEPRIN.CIDADE, CIDADE_ALT.CIDADE) AS CIDADE_ENTREGA,
                COALESCE(CIDADEPRIN.UF, CIDADE_ALT.UF) AS UF_ENTREGA,
                -- Dados do produto
                PRODUTO.CPRODUTO AS PRODUTO_CODIGO,
                PRODUTO.REF_FORNECE AS PRODUTO_REFERENCIA,
                PRODUTO.DESCRICAO AS PRODUTO_DESCRICAO,
                -- Dados do item do pedido
                ITEM.PREVDT AS PEDIDO_PREVISAO,
                ITEM.QTDE AS PEDIDO_QUANTIDADE,
                COALESCE(BAIXA.QUANTIDADE, 0) AS PEDIDO_BAIXA_MANUAL,
                COALESCE(NOTA.QUANTIDADE, 0) AS PEDIDO_BAIXA,
                ITEM.UNITARIO AS PEDIDO_VALOR_UNITARIO,
                COALESCE(PEDIDO.PEDIDOAPROV, 'N') AS PEDIDO_APROVADO,
                -- Dados da nota fiscal
                NFSAIDA.NFS AS SEQUENCIAL_TECNICON,
                NFSAIDA.NF AS NF_NUMERO,
                NFSAIDA.DATA AS NF_DATA,
                NFSITEM.QTDE AS NF_QUANTIDADE,
                NFSITEM.UNITARIOCLI AS NF_VALOR_UNITARIO,
                NFSITEM.TOTAL AS NF_TOTAL_ITEM,
                NFSAIDA.VALOR_TOTAL,
                CHAVENFE.NFS AS NOTAXML, 
                CHAVENFEXML.NFEXML AS XML,
                -- Saldo do pedido
                (ITEM.QTDE - COALESCE(BAIXA.QUANTIDADE, 0) - COALESCE(NOTA.QUANTIDADE, 0)) AS PEDIDO_SALDO
            FROM PEDIDOITEM AS ITEM
            JOIN PEDIDO USING(PEDIDO)
            JOIN CLIFOR USING(CCLIFOR)
            JOIN PRODUTO USING(CPRODUTO)
            JOIN CIOF ON ITEM.CIOF = CIOF.CIOF
            LEFT JOIN (
                SELECT PEDIDOITEM, SUM(QTDE) AS QUANTIDADE
                FROM PEDIDOITEMBX
                GROUP BY PEDIDOITEM
            ) AS BAIXA USING(PEDIDOITEM)
            LEFT JOIN (
                SELECT PEDIDOITEM, SUM(QTDE) AS QUANTIDADE
                FROM NFSITEM
                GROUP BY PEDIDOITEM
            ) AS NOTA USING(PEDIDOITEM)
            LEFT JOIN NFSITEM ON NFSITEM.PEDIDOITEM = ITEM.PEDIDOITEM
            LEFT JOIN NFSAIDA ON NFSAIDA.NFS = NFSITEM.NFS
            JOIN CLIFOR AS REVENDA ON PEDIDO.CREVENDA = REVENDA.CCLIFOR
            LEFT JOIN (
                SELECT 
                    CCLIFOR,
                    MIN(ENDERECO) AS ENDERECO,
                    MIN(NUMERO) AS NUMERO,
                    MIN(CCIDADE) AS CCIDADE
                FROM CLIFOREND
                GROUP BY CCLIFOR
            ) AS CLIFOREND_UNICO ON CLIFOR.CCLIFOR = CLIFOREND_UNICO.CCLIFOR
            LEFT JOIN CIDADE AS CIDADE_ALT ON CLIFOREND_UNICO.CCIDADE = CIDADE_ALT.CCIDADE
            LEFT JOIN CLIENDENT ON PEDIDO.SCLIENDENT = CLIENDENT.SCLIENDENT
            LEFT JOIN CIDADE AS CIDADEPRIN ON CLIENDENT.CCIDADE = CIDADEPRIN.CCIDADE
            LEFT JOIN CHAVENFE ON CHAVENFE.NFS = NFSAIDA.NFS
            LEFT JOIN CHAVENFEXML ON CHAVENFEXML.SCHAVENFE = CHAVENFE.SCHAVENFE
            WHERE PEDIDO.DATA >= '2022-01-01'
              AND PEDIDO.CCLIFOR = ?
        )
        SELECT
            DISTINCT VT.*,
            (VT.PEDIDO_SALDO * VT.PEDIDO_VALOR_UNITARIO) AS PEDIDO_VALOR_TOTAL,
            CASE
                WHEN VT.PEDIDO_QUANTIDADE = 0 THEN 'Pedido Incluído'
                WHEN VT.PEDIDO_BAIXA > 0 AND VT.PEDIDO_BAIXA < VT.PEDIDO_QUANTIDADE THEN 'Faturamento Parcial'
                WHEN VT.PEDIDO_BAIXA >= VT.PEDIDO_QUANTIDADE THEN 'Faturamento Integral'
                ELSE 'Pedido Incluído'
            END AS STATUS_PEDIDO
        FROM VT;
        """
        cursor.execute(query, (codigo_cliente,))
        colunas = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        pedidos = [dict(zip(colunas, row)) for row in rows]
        cursor.close()
        conn.close()
        return pedidos
    except Exception as e:
        logger.error(f"Erro ao listar pedidos (modo cliente) para {codigo_cliente}: {e}", exc_info=True)
        return []


def listar_pedidos_da_revenda(codigo_revenda):
    """
    Retorna todos os pedidos da revenda (PEDIDO.CREVENDA) no Firebird utilizando a query atualizada.
    """
    logger.info(f"Buscando pedidos da revenda (CREVENDA) = {codigo_revenda} no Firebird.")
    try:
        conn = get_firebird_connection()
        cursor = conn.cursor()
        query = """
        WITH VT AS (
            SELECT 
                PEDIDO.CFILIAL, 
                PEDIDO."DATA" AS DT_INCLUSAO,
                PEDIDO.PEDIDO,
                PEDIDO.CREVENDA AS COD_REVENDA,
                REVENDA.NOME AS REVENDA,
                PEDIDO.CVENDEDOR, 
                PEDIDO.CCLIFOR AS COD_CLIENTE,
                PEDIDO.PREVDT AS DATA_ENTREGA,
                CLIFOR.NOME AS NOME_CLIENTE,
                PEDIDO.FILIALCF,
                CLIFOREND_UNICO.ENDERECO AS ENDERECO_ALTERNATIVO,
                CLIFOREND_UNICO.NUMERO AS NUMERO_ALTERNATIVO,
                CLIFOREND_UNICO.CCIDADE AS COD_CIDADE_ALTERNATIVO,
                CIDADE_ALT.CIDADE AS CIDADE_ALTERNATIVO,
                CIDADE_ALT.UF AS UF_ALTERNATIVO,
                CLIENDENT.ENDERECO AS ENDERECO_PRINCIPAL,
                CLIENDENT.NUMERO AS NUMERO_PRINCIPAL,
                CLIENDENT.CCIDADE AS COD_CLIENTE_PRINCIPAL,
                CIDADEPRIN.CIDADE AS CIDADE_PRINCIPAL,
                CIDADEPRIN.UF AS UF_PRINCIPAL,
                COALESCE(CLIENDENT.ENDERECO, CLIFOREND_UNICO.ENDERECO) AS ENDERECO_ENTREGA,
                COALESCE(CLIENDENT.NUMERO, CLIFOREND_UNICO.NUMERO) AS NUMERO_ENTREGA,
                COALESCE(CIDADEPRIN.CIDADE, CIDADE_ALT.CIDADE) AS CIDADE_ENTREGA,
                COALESCE(CIDADEPRIN.UF, CIDADE_ALT.UF) AS UF_ENTREGA,
                PRODUTO.CPRODUTO AS PRODUTO_CODIGO,
                PRODUTO.REF_FORNECE AS PRODUTO_REFERENCIA,
                PRODUTO.DESCRICAO AS PRODUTO_DESCRICAO,
                ITEM.PREVDT AS PEDIDO_PREVISAO,
                ITEM.QTDE AS PEDIDO_QUANTIDADE,
                COALESCE(BAIXA.QUANTIDADE, 0) AS PEDIDO_BAIXA_MANUAL,
                COALESCE(NOTA.QUANTIDADE, 0) AS PEDIDO_BAIXA,
                ITEM.UNITARIO AS PEDIDO_VALOR_UNITARIO,
                COALESCE(PEDIDO.PEDIDOAPROV, 'N') AS PEDIDO_APROVADO,
                NFSAIDA.NFS AS SEQUENCIAL_TECNICON,
                NFSAIDA.NF AS NF_NUMERO,
                NFSAIDA.DATA AS NF_DATA,
                NFSITEM.QTDE AS NF_QUANTIDADE,
                NFSITEM.UNITARIOCLI AS NF_VALOR_UNITARIO,
                NFSITEM.TOTAL AS NF_TOTAL_ITEM,
                NFSAIDA.VALOR_TOTAL,
                CHAVENFE.NFS AS NOTAXML, 
                CHAVENFEXML.NFEXML AS XML,
                (ITEM.QTDE - COALESCE(BAIXA.QUANTIDADE, 0) - COALESCE(NOTA.QUANTIDADE, 0)) AS PEDIDO_SALDO
            FROM PEDIDOITEM AS ITEM
            JOIN PEDIDO USING(PEDIDO)
            JOIN CLIFOR USING(CCLIFOR)
            JOIN PRODUTO USING(CPRODUTO)
            JOIN CIOF ON ITEM.CIOF = CIOF.CIOF
            LEFT JOIN (
                SELECT PEDIDOITEM, SUM(QTDE) AS QUANTIDADE
                FROM PEDIDOITEMBX
                GROUP BY PEDIDOITEM
            ) AS BAIXA USING(PEDIDOITEM)
            LEFT JOIN (
                SELECT PEDIDOITEM, SUM(QTDE) AS QUANTIDADE
                FROM NFSITEM
                GROUP BY PEDIDOITEM
            ) AS NOTA USING(PEDIDOITEM)
            LEFT JOIN NFSITEM ON NFSITEM.PEDIDOITEM = ITEM.PEDIDOITEM
            LEFT JOIN NFSAIDA ON NFSAIDA.NFS = NFSITEM.NFS
            JOIN CLIFOR AS REVENDA ON PEDIDO.CREVENDA = REVENDA.CCLIFOR
            LEFT JOIN (
                SELECT 
                    CCLIFOR,
                    MIN(ENDERECO) AS ENDERECO,
                    MIN(NUMERO) AS NUMERO,
                    MIN(CCIDADE) AS CCIDADE
                FROM CLIFOREND
                GROUP BY CCLIFOR
            ) AS CLIFOREND_UNICO ON CLIFOR.CCLIFOR = CLIFOREND_UNICO.CCLIFOR
            LEFT JOIN CIDADE AS CIDADE_ALT ON CLIFOREND_UNICO.CCIDADE = CIDADE_ALT.CCIDADE
            LEFT JOIN CLIENDENT ON PEDIDO.SCLIENDENT = CLIENDENT.SCLIENDENT
            LEFT JOIN CIDADE AS CIDADEPRIN ON CLIENDENT.CCIDADE = CIDADEPRIN.CCIDADE
            LEFT JOIN CHAVENFE ON CHAVENFE.NFS = NFSAIDA.NFS
            LEFT JOIN CHAVENFEXML ON CHAVENFEXML.SCHAVENFE = CHAVENFE.SCHAVENFE
            WHERE PEDIDO.DATA >= '2022-01-01'
              AND PEDIDO.CREVENDA = ?
        )
        SELECT
            DISTINCT VT.*,
            (VT.PEDIDO_SALDO * VT.PEDIDO_VALOR_UNITARIO) AS PEDIDO_VALOR_TOTAL,
            CASE
                WHEN VT.PEDIDO_QUANTIDADE = 0 THEN 'Pedido Incluído'
                WHEN VT.PEDIDO_BAIXA > 0 AND VT.PEDIDO_BAIXA < VT.PEDIDO_QUANTIDADE THEN 'Faturamento Parcial'
                WHEN VT.PEDIDO_BAIXA >= VT.PEDIDO_QUANTIDADE THEN 'Faturamento Integral'
                ELSE 'Pedido Incluído'
            END AS STATUS_PEDIDO
        FROM VT;
        """
        cursor.execute(query, (codigo_revenda,))
        colunas = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        pedidos = [dict(zip(colunas, row)) for row in rows]
        cursor.close()
        conn.close()
        return pedidos
    except Exception as e:
        logger.error(f"Erro ao listar pedidos (modo revenda) para {codigo_revenda}: {e}", exc_info=True)
        return []


def buscar_xml_nf(numero_nfs):
    logger.info("Iniciando busca para NFS %s", numero_nfs)
    conn = conectar_firebird()
    if not conn:
        logger.error("Falha ao conectar ao banco Firebird!")
        return None
    try:
        cursor = conn.cursor()
        sql = """
        WITH VT AS (
            SELECT 
                NFSAIDA.NFS AS SEQUENCIAL_TECNICON,
                CHAVENFEXML.NFEXML AS XML
            FROM NFSAIDA
            JOIN CHAVENFE ON CHAVENFE.NFS = NFSAIDA.NFS
            JOIN CHAVENFEXML ON CHAVENFEXML.SCHAVENFE = CHAVENFE.SCHAVENFE
            WHERE CHAVENFE.NFESTATUS = 'A'
              AND CHAVENFE.NFS = ?
        )
        SELECT XML FROM VT;
        """
        logger.debug("SQL a ser executado: %s", sql)
        logger.debug("Parâmetro para busca: %s", numero_nfs)
        cursor.execute(sql, (numero_nfs,))
        resultado = cursor.fetchone()
        if not resultado:
            logger.warning("NFS %s não encontrada no banco!", numero_nfs)
            return None
        xml_content = resultado[0]
        if not xml_content:
            logger.warning("NFS %s encontrada, mas sem XML armazenado!", numero_nfs)
            return None
        logger.debug("Trecho do XML para NFS %s: %s", numero_nfs, xml_content[:500])
        try:
            nfe_dict = xmltodict.parse(xml_content)
            numero_nf_impresso = (
                nfe_dict.get('nfeProc', {})
                         .get('NFe', {})
                         .get('infNFe', {})
                         .get('ide', {})
                         .get('nNF', 'N/A')
            )
            logger.info("XML encontrado para NFS %s. Número NF (impresso): %s.", numero_nfs, numero_nf_impresso)
            return xml_content
        except Exception as e:
            logger.error("Erro ao converter XML da NFS %s: %s", numero_nfs, e)
            return None
    except Exception as e:
        logger.error("Erro ao buscar NFS %s no banco: %s", numero_nfs, e, exc_info=True)
        return None
    finally:
        conn.close()
        logger.debug("Conexão com o banco Firebird fechada.")


def gerar_danfe_em_pdf(xml_content):
    """
    Gera um DANFE (PDF) a partir do XML da nota fiscal. Exemplo utilizando reportlab.
    """
    from io import BytesIO
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 800, "DANFE Gerada - Exemplo PDF")
    p.drawString(100, 780, "----------------------------------")
    p.drawString(100, 760, f"Trecho XML: {xml_content[:200]}...")
    p.drawString(100, 740, "(PDF placeholder)")
    p.showPage()
    p.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

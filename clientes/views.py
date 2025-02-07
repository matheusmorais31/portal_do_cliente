import logging
import xmltodict
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test, login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from .utils import get_firebird_connection
from .models import ClienteProfile
from .forms import ClienteImportForm, ClienteSenhaForm
from .utils import (
    listar_clientes_disponiveis,
    importar_clientes,
    listar_pedidos_do_cliente,
    listar_pedidos_da_revenda,
    buscar_xml_nf,
    gerar_danfe_em_pdf
)

logger = logging.getLogger(__name__)
User = get_user_model()


def is_staff_user(user):
    return user.is_staff


@user_passes_test(is_staff_user)
def listar_clientes_disponiveis_view(request):
    """Listar clientes disponíveis para importação."""
    logger.info("Recebendo requisição para listar clientes disponíveis.")
    try:
        clientes = listar_clientes_disponiveis()
        logger.debug(f"Clientes disponíveis para importação: {len(clientes)} encontrados.")
        choices = [
            (cliente["CNPJ_CPF"],
             f"{cliente['RAZAO_SOCIAL']} ({cliente.get('CLASSIFICACAO', 'Sem Classificação')})")
            for cliente in clientes
        ]
        if request.method == 'POST':
            form = ClienteImportForm(request.POST)
            form.fields['clientes'].choices = choices
            if form.is_valid():
                selected_clientes = form.cleaned_data['clientes']
                total_importados = importar_clientes(clientes_selecionados=selected_clientes)
                if total_importados > 0:
                    messages.success(request, f"{total_importados} clientes importados com sucesso.")
                else:
                    messages.warning(request, "Nenhum cliente foi importado.")
                return redirect('clientes:importar_clientes')
        else:
            form = ClienteImportForm()
            form.fields['clientes'].choices = choices
        return render(request, 'clientes/importar_clientes.html', {'form': form})
    except Exception as e:
        logger.error(f"Erro na view listar_clientes_disponiveis_view: {e}", exc_info=True)
        messages.error(request, "Ocorreu um erro ao listar os clientes disponíveis.")
        return redirect('clientes:listar_clientes')


@user_passes_test(is_staff_user)
def buscar_clientes(request):
    """Busca dinâmica de clientes."""
    logger.info("Recebendo requisição para buscar clientes.")
    try:
        query = request.GET.get('q', '').strip().lower()
        clientes = listar_clientes_disponiveis()
        filtered_clientes = []
        for cliente in clientes:
            cnpj_cpf = (cliente.get("CNPJ_CPF") or "").lower()
            razao_social = (cliente.get("RAZAO_SOCIAL") or "").lower()
            if query in cnpj_cpf or query in razao_social:
                filtered_clientes.append({
                    "value": cliente["CNPJ_CPF"],
                    "label": f"{cliente['RAZAO_SOCIAL']} ({cliente.get('CLASSIFICACAO', '')})"
                })
        return JsonResponse(filtered_clientes, safe=False)
    except Exception as e:
        logger.error(f"Erro na busca de clientes: {e}", exc_info=True)
        return JsonResponse([], safe=False)


@user_passes_test(is_staff_user)
def listar_clientes_view(request):
    """Lista clientes já importados."""
    logger.info("Recebendo requisição para listar clientes já importados.")
    try:
        usuarios = User.objects.filter(clienteprofile__isnull=False).select_related('clienteprofile')
        paginator = Paginator(usuarios, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        return render(request, 'clientes/listar_clientes.html', {'page_obj': page_obj})
    except Exception as e:
        logger.error(f"Erro na view listar_clientes_view: {e}", exc_info=True)
        messages.error(request, "Ocorreu um erro ao listar os clientes.")
        return redirect('clientes:importar_clientes')


@user_passes_test(is_staff_user)
def editar_cliente_senha(request, cliente_id):
    """Altera a senha de um cliente específico (sem exigir senha antiga)."""
    cliente_profile = get_object_or_404(ClienteProfile, id=cliente_id)
    user = cliente_profile.user
    if request.method == 'POST':
        form = ClienteSenhaForm(request.POST, instance=user)
        if form.is_valid():
            nova_senha = form.cleaned_data['nova_senha']
            user.set_password(nova_senha)
            user.save()
            messages.success(request, f"A senha do cliente {cliente_profile.razao_social} foi alterada com sucesso.")
            return redirect('clientes:listar_clientes')
        else:
            messages.error(request, "Erro ao alterar a senha. Verifique o formulário.")
    else:
        form = ClienteSenhaForm(instance=user)
    return render(request, 'clientes/editar_senha.html', {'form': form, 'cliente': cliente_profile})


@login_required
def meus_pedidos_view(request):
    """
    Exibe os pedidos do cliente logado (filtrados por PEDIDO.CCLIFOR).
    Certifique-se de que o link para a DANFE utiliza o valor de SEQUENCIAL_TECNICON.
    """
    user = request.user
    try:
        cliente_profile = user.clienteprofile
    except ClienteProfile.DoesNotExist:
        messages.error(request, "Não há perfil de cliente para este usuário.")
        return render(request, 'clientes/meus_pedidos.html', {'pedidos': []})
    codigo_cliente = cliente_profile.codigo_cliente
    pedidos = listar_pedidos_do_cliente(codigo_cliente)
    for pedido in pedidos:
        status = (pedido.get('STATUS_PEDIDO') or '').strip()
        pedido['is_included'] = True
        pedido['is_partial'] = status in ['Faturamento Parcial', 'Faturamento Integral']
        pedido['is_integral'] = (status == 'Faturamento Integral')
    
    # Log para cada pedido (ou grupo, se você quiser ver os NF únicos)
    for pedido in pedidos:
        nf_numero = pedido.get('NF_NUMERO', '')
        nfs = pedido.get('NOTAXML', '')
        logger.debug("Pedido id: %s | NF_NUMERO: %s | NOTAXML: %s", pedido.get('PEDIDO'), nf_numero, nfs)

    logger.debug("Total de pedidos: %s", len(pedidos))
    return render(request, 'clientes/meus_pedidos.html', {'pedidos': pedidos})


@login_required
def pedidos_meus_clientes_view(request):
    """
    Exibe os pedidos dos clientes vinculados à revenda (filtrados por PEDIDO.CREVENDA).
    Certifique-se de que o link para a DANFE utiliza o valor de SEQUENCIAL_TECNICON.
    """
    user = request.user
    try:
        cliente_profile = user.clienteprofile
    except ClienteProfile.DoesNotExist:
        messages.error(request, "Não há perfil de revenda para este usuário.")
        return render(request, 'clientes/pedidos_meus_clientes.html', {'pedidos': []})
    codigo_revenda = cliente_profile.codigo_cliente
    pedidos = listar_pedidos_da_revenda(codigo_revenda)
    for pedido in pedidos:
        status = (pedido.get('STATUS_PEDIDO') or '').strip()
        pedido['is_included'] = True
        pedido['is_partial'] = status in ['Faturamento Parcial', 'Faturamento Integral']
        pedido['is_integral'] = (status == 'Faturamento Integral')
    return render(request, 'clientes/pedidos_meus_clientes.html', {'pedidos': pedidos})


@login_required
def download_danfe(request, nf_numero):
    """
    Gera o PDF do DANFE para o número impresso da nota fiscal (NF).
    Nesta função, convertemos o número impresso (NF) para o identificador interno (NFS)
    utilizando uma query que retorna o registro mais recente (FIRST 1 e ORDER BY).
    """
    logger.info(f"Tentando gerar DANFE para NF (impresso) {nf_numero}")
    try:
        conn = get_firebird_connection()
        cursor = conn.cursor()
        sql = """
        SELECT FIRST 1 NFSAIDA.NFS
          FROM NFSAIDA
          JOIN CHAVENFE ON CHAVENFE.NFS = NFSAIDA.NFS
         WHERE NFSAIDA.NF = ?
           AND CHAVENFE.NFESTATUS = 'A'
         ORDER BY NFSAIDA.NFS DESC
        """
        cursor.execute(sql, (nf_numero,))
        row = cursor.fetchone()
        if not row:
            messages.error(request, f"Não foi possível encontrar o identificador interno para NF {nf_numero}.")
            return redirect('clientes:meus_pedidos')
        sequencial_tecnicon = row[0]
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Erro ao converter NF para NFS: {e}", exc_info=True)
        messages.error(request, "Erro ao processar a nota fiscal.")
        return redirect('clientes:meus_pedidos')
    
    # Busca o XML utilizando o identificador interno
    xml_content = buscar_xml_nf(sequencial_tecnicon)
    if not xml_content:
        messages.error(request, f"Não foi encontrado XML para o identificador {sequencial_tecnicon}.")
        return redirect('clientes:meus_pedidos')
    
    danfe_pdf = gerar_danfe_em_pdf(xml_content)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="danfe_{sequencial_tecnicon}.pdf"'
    response.write(danfe_pdf)
    return response



def remove_namespace(xml):
    """
    Remove os namespaces do XML para facilitar o parse com xmltodict.
    Essa função remove o xmlns padrão e quaisquer prefixos de tags.
    """
    # Remove o namespace padrão
    xml = re.sub(r'\sxmlns="[^"]+"', '', xml, count=1)
    # Remove quaisquer prefixos (ex.: ns:)
    xml = re.sub(r'(<\/?)[\w0-9]+:(\w+)', r'\1\2', xml)
    return xml

@login_required
def visualizar_danfe_html(request, nf_numero):
    """
    Exibe a DANFE em HTML.
    
    Este view realiza os seguintes passos:
      1. Converte o número impresso da NF para o identificador interno (NFS)
         realizando uma query no banco.
      2. Busca o XML da NF (através do NFS) e, se necessário, decodifica-o.
      3. Remove os namespaces do XML para facilitar o parse.
      4. Converte o XML para um dicionário e extrai os nós relevantes, inclusive o de
         transporte e volume. Se o elemento <vol> vier como lista, seleciona o primeiro item.
      5. Monta o dicionário `note` e renderiza o template da DANFE.
    """
    logger.info(f"Visualizando DANFE para NF {nf_numero}.")
    try:
        # 1. Recupera o identificador interno (NFS) correspondente à NF informada.
        conn = get_firebird_connection()
        cursor = conn.cursor()
        sql = """
        SELECT FIRST 1 NFSAIDA.NFS
          FROM NFSAIDA
          JOIN CHAVENFE ON CHAVENFE.NFS = NFSAIDA.NFS
         WHERE NFSAIDA.NF = ?
           AND CHAVENFE.NFESTATUS = 'A'
         ORDER BY NFSAIDA.NFS DESC
        """
        cursor.execute(sql, (nf_numero,))
        row = cursor.fetchone()
        if not row:
            messages.error(request, f"NF {nf_numero} não encontrada.")
            return redirect('clientes:meus_pedidos')
        sequencial_tecnicon = row[0]
        cursor.close()
        conn.close()

        # 2. Busca o XML utilizando o identificador interno (NFS).
        xml_content = buscar_xml_nf(sequencial_tecnicon)
        if not xml_content:
            messages.error(request, f"XML da NF {nf_numero} não encontrado.")
            return redirect('clientes:meus_pedidos')

        # Se o conteúdo do XML estiver em bytes, decodifica para string.
        if isinstance(xml_content, bytes):
            xml_content = xml_content.decode("utf-8", errors="ignore")

        # 3. Remove os namespaces do XML para facilitar o parse.
        xml_clean = remove_namespace(xml_content)

        # 4. Converte o XML para dicionário e extrai os dados relevantes.
        nfe_dict = xmltodict.parse(xml_clean)
        if "nfeProc" not in nfe_dict:
            raise ValueError("Formato inválido: tag 'nfeProc' não encontrada.")

        inf_nfe = nfe_dict.get("nfeProc", {}).get("NFe", {}).get("infNFe", {})

        # Tratamento do nó de transporte (transp) e do volume (vol)
        transp = inf_nfe.get("transp", {})
        vol = transp.get("vol")
        if vol:
            if isinstance(vol, list):
                # Se houver mais de um volume, seleciona o primeiro (ou adapte conforme necessário)
                transp["vol"] = vol[0]
            elif not isinstance(vol, dict):
                # Caso vol não seja um dicionário, garante que seja um dicionário vazio
                transp["vol"] = {}
        else:
            # Caso não exista o elemento <vol> no XML, cria uma chave vazia para evitar erros no template
            transp["vol"] = {}

        # Monta o dicionário com os dados da NF-e para uso no template.
        note = {
            'ide': inf_nfe.get('ide', {}),
            'emit': inf_nfe.get('emit', {}),
            'dest': inf_nfe.get('dest', {}),
            'total': inf_nfe.get('total', {}).get('ICMSTot', {}),
            'transp': transp,
            'det': inf_nfe.get('det', []),
            'prot': nfe_dict.get('nfeProc', {}).get('protNFe', {}).get('infProt', {}),
            'infAdic': inf_nfe.get('infAdic', {}).get('infCpl', '')
        }
        # Se o nó 'det' vier como dicionário único, converte-o para lista.
        if isinstance(note['det'], dict):
            note['det'] = [note['det']]

        # 5. Renderiza o template, passando o dicionário e o endereço do logo.
        logo_url = request.build_absolute_uri(static('images/logo.png'))
        context = {'note': note, 'logo_url': logo_url}
        return render(request, 'clientes/danfe_html.html', context)
    except Exception as e:
        logger.error("Erro ao processar DANFE: %s", e, exc_info=True)
        messages.error(request, f"Ocorreu um erro ao exibir a DANFE. {e}")
        return redirect('clientes:meus_pedidos')
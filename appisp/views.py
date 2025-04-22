import requests
from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from dal import autocomplete
import platform
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from rest_framework.authentication import TokenAuthentication
from django.db.models import Prefetch
from concurrent.futures import ThreadPoolExecutor
import subprocess
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, authentication_classes
from .authentication import EmpresaTokenAuthentication
from .models import Porta, Empresa, Pop, Rack, Equipamento, BlocoIP, EnderecoIP, VlanPorta, Vlan, EmpresaToken, \
                    IntegracaoZabbix
from .forms import PortaForm, EnderecoIPForm
from rest_framework.permissions import BasePermission
import json
from rest_framework.response import Response

def get_equipamento(request, equipamento_id):
    try:
        equipamento = Equipamento.objects.get(id=equipamento_id)
        data = {
            'id': equipamento.id,
            'nome': equipamento.nome,
            'ip': equipamento.ip,
            'usuario': equipamento.usuario,
            'senha': equipamento.senha,
            'porta': equipamento.porta,
            'protocolo': equipamento.protocolo,
            'status': equipamento.status,
            'observacao': equipamento.observacao,
        }
        return JsonResponse(data)
    except Equipamento.DoesNotExist:
        return JsonResponse({'error': 'Equipamento não encontrado'}, status=404)


def ping(ip):
    try:
        # Verifica o sistema operacional
        if platform.system().lower() == "windows":
            response = subprocess.run(
                ["ping", "-n", "1", ip],  # Windows
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2
            )
        else:
            response = subprocess.run(
                ["ping", "-c", "1", ip],  # Linux
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2
            )

        return {"ip": ip, "status": "online" if response.returncode == 0 else "offline"}
    except Exception as e:
        print(f"Error pinging {ip}: {e}")
        return {"ip": ip, "status": "offline"}


def verificar_status_equipamentos(request):
    # Obtemos todos os equipamentos
    equipamentos = Equipamento.objects.all()

    with ThreadPoolExecutor(max_workers=10) as executor:
        # Realizamos o ping para cada equipamento
        resultados = list(executor.map(ping, [equipamento.ip for equipamento in equipamentos]))

    # Atualizamos o status dos equipamentos com base no ping
    for equipamento, resultado in zip(equipamentos, resultados):
        if resultado["status"] == "online":
            equipamento.status = "Ativo"
        else:
            equipamento.status = "Inativo"
        equipamento.save()  # Salva a alteração no banco de dados

    return JsonResponse(resultados, safe=False)


def adicionar_endereco_ip(request):
    user = request.user

    if request.method == "POST":
        form = EnderecoIPForm(request.POST, user=user)  # Passa o usuário para o formulário
        if form.is_valid():
            form.save()
            # messages.success(request, "Endereço IP adicionado com sucesso!")
            return redirect("/admin/appisp/enderecoip")  # Substitua pelo nome correto da URL
    else:
        form = EnderecoIPForm(user=user)  # Passa o usuário para o formulário

    return render(request, "appisp/endereco_ip.html", {"form": form})


class TokenRequiredPermission(BasePermission):
    def has_permission(self, request, view):
        # Verifica se o cabeçalho Authorization contém um token válido
        token = request.headers.get("Authorization")
        if not token:
            return False

        # Remove a palavra "Token " do início, caso exista
        if token.startswith("Token "):
            token = token.split("Token ")[1]

        try:
            # Valida o token
            empresa_token = EmpresaToken.objects.get(token=token)
            return True
        except EmpresaToken.DoesNotExist:
            return False


class DisableSessionAuthenticationMiddleware:
    """
    Middleware para desabilitar a autenticação de sessão em algumas rotas
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Desabilitar a autenticação de sessão apenas para rotas específicas de API
        if request.path.startswith('/api/'):
            request.session = None  # Remover a sessão
        response = self.get_response(request)
        return response


@api_view(['PATCH'])  # Usamos PATCH para alterar apenas um campo
@authentication_classes([EmpresaTokenAuthentication])
def atualizar_status_equipamento(request, equipamento_id):
    token = request.headers.get("Authorization")

    if not token:
        return JsonResponse({"error": "Token não fornecido"}, status=401)

    try:
        empresa_token = EmpresaToken.objects.get(token=token)
        equipamento = Equipamento.objects.get(id=equipamento_id, empresa=empresa_token.empresa)

        novo_status = request.data.get("status")
        if novo_status is None:
            return JsonResponse({"error": "O campo 'status' é obrigatório."}, status=400)

        equipamento.status = novo_status
        equipamento.save()

        return JsonResponse(
            {"message": "Status atualizado com sucesso!", "id": equipamento.id, "novo_status": equipamento.status})

    except EmpresaToken.DoesNotExist:
        return JsonResponse({"error": "Token inválido"}, status=403)
    except Equipamento.DoesNotExist:
        return JsonResponse({"error": "Equipamento não encontrado"}, status=404)


@api_view(['GET'])
@authentication_classes([TokenAuthentication])  # Garantir que somente o TokenAuthentication será usado
def listar_equipamentosApi(request):
    token = request.headers.get("Authorization")

    if not token:
        return JsonResponse({"error": "Token não fornecido"}, status=401)

    if token.startswith("Token "):
        token = token.split("Token ")[1]

    try:
        empresa_token = EmpresaToken.objects.get(token=token)

        equipamentos = Equipamento.objects.filter(empresa=empresa_token.empresa).values("id", "nome", "ip", "status")

        return JsonResponse(list(equipamentos), safe=False)
    except EmpresaToken.DoesNotExist:
        return JsonResponse({"error": "Token inválido"}, status=403)


def get_equipamentos(request):
    empresa_id = request.GET.get("empresa_id")
    if empresa_id:
        equipamentos = Equipamento.objects.filter(empresa_id=empresa_id).values("id", "nome")
        return JsonResponse(list(equipamentos), safe=False)
    return JsonResponse([], safe=False)


def get_ips(request):
    blocos = BlocoIP.objects.all()
    data = []

    for bloco in blocos:
        sub_blocos = bloco.sub_blocos.all()
        enderecos = EnderecoIP.objects.filter(bloco=bloco)

        bloco_data = {
            "id": bloco.id,
            "subnet": bloco.bloco_cidr,
            "ips": [
                {"ip": ip.ip, "equipamento": ip.equipamento.nome if ip.equipamento else "Livre"}
                for ip in enderecos
            ],
            "sub_blocos": [
                {"id": sub.id, "subnet": sub.bloco_cidr} for sub in sub_blocos
            ]
        }
        data.append(bloco_data)

    return JsonResponse({"blocos": data})


def ip_management_view(request):
    return render(request, "ip_management.html")


def api_portas(request):
    equipamento_id = request.GET.get('equipamento_id')

    if equipamento_id:
        try:
            # Convertendo o equipamento_id para um número inteiro
            equipamento_id = int(equipamento_id)

            # Filtrando as portas do equipamento e garantindo que a porta não tenha uma conexão
            portas = Porta.objects.filter(
                equipamento_id=equipamento_id,
                conexao__isnull=True  # Garante que a porta não está conectada
            ).values('id', 'nome', 'tipo', 'speed')

            if portas.exists():  # Verifique se existem portas
                return JsonResponse(list(portas), safe=False)
            else:
                # Em vez de retornar 404, retornamos 200 com a mensagem de erro
                return JsonResponse({"error": "Nenhuma porta livre encontrada."}, status=200)

        except ValueError:
            return JsonResponse({"error": "ID inválido."}, status=400)
    else:
        return JsonResponse({"error": "Equipamento ID não fornecido."}, status=400)


@api_view(['POST'])
def conectar_portas(request):
    try:
        data = request.data

        porta_origem_id = data.get("porta_origem_id")
        porta_destino_id = data.get("porta_destino_id")
        observacao = data.get("observacao")  # Captura o campo observação da requisição

        if not all([porta_origem_id, porta_destino_id]):
            return Response({"error": "IDs das portas são obrigatórios"}, status=400)

        with transaction.atomic():  # Garante consistência no banco de dados
            porta_origem = Porta.objects.get(id=porta_origem_id)
            porta_destino = Porta.objects.get(id=porta_destino_id)

            # Se a porta de origem já está conectada, removemos a conexão antiga
            if porta_origem.conexao:
                porta_origem.conexao.conexao = None  # Remove a conexão inversa da outra porta
                porta_origem.conexao.save(update_fields=['conexao'])
                porta_origem.conexao = None
                porta_origem.save(update_fields=['conexao'])

            # Se a porta de destino já está conectada, removemos a conexão antiga
            if porta_destino.conexao:
                porta_destino.conexao.conexao = None  # Remove a conexão inversa da outra porta
                porta_destino.conexao.save(update_fields=['conexao'])
                porta_destino.conexao = None
                porta_destino.save(update_fields=['conexao'])

            # Criar a nova conexão
            porta_origem.conexao = porta_destino
            porta_origem.save(update_fields=['conexao'])

            # Agora salvamos a observação na porta de destino
            porta_destino.observacao = observacao  # Atualiza a observação na porta de destino
            porta_destino.save(update_fields=['observacao'])

        return Response({"message": "Portas conectadas com sucesso!"}, status=200)

    except Porta.DoesNotExist:
        return Response({"error": "Uma ou ambas as portas não foram encontradas"}, status=404)
    except Exception as e:
        return Response({"error": f"Erro inesperado: {str(e)}"}, status=500)


@api_view(['POST'])
def desconectar_portas(request):
    porta_id = request.data.get('porta_id')

    if not porta_id:
        return Response({"success": False, "error": "ID da porta não fornecido."}, status=400)

    try:
        porta = Porta.objects.get(id=porta_id)
        porta.conexao = None
        porta.save()
        return Response({"success": True})
    except Porta.DoesNotExist:
        return Response({"success": False, "error": "Porta não encontrada."}, status=404)
    except Exception as e:
        return Response({"success": False, "error": str(e)}, status=500)


def get_portas(request):
    equipamento_id = request.GET.get("equipamento_id")
    if equipamento_id:
        portas = Porta.objects.filter(equipamento_id=equipamento_id).values("id", "nome")
        return JsonResponse(list(portas), safe=False)
    return JsonResponse([], safe=False)


@login_required
def adicionar_portas(request):
    if request.method == "POST":
        print("🚀 Dados Recebidos views:", request.POST)
        form = PortaForm(request.POST)

        if form.is_valid():
            print("✅ Empresa Selecionada views:", form.cleaned_data["empresa"])
            form.save()
            return redirect("/admin")  # Substitua pelo nome correto da URL
    else:
        form = PortaForm()
        print("❌ Erros no formulário:", form.errors)  # Verifica os erros

    print(form.errors)  # Verifica erros no formulário
    return render(request, "adicionar_lote.html", {"form": form})


@login_required
def listar_equipamentos(request):
    usuario = request.user
    empresas_do_usuario = usuario.empresas.all()  # Obtém todas as empresas associadas ao usuário

    equipamentos = Equipamento.objects.filter(empresa__in=empresas_do_usuario)  # Filtra os equipamentos

    return render(request, 'equipamentos_list.html', {'equipamentos': equipamentos})


class EmpresaForm(forms.ModelForm):
    usuarios = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # Lista de checkboxes para múltiplos usuários
        required=False
    )

    class Meta:
        model = Empresa
        fields = ['nome', 'endereco', 'cidade', 'estado', 'telefone', 'cpf_cnpj', 'representante', 'email', 'status',
                  'usuarios']


# View para exibir o mapa de Racks
@login_required(login_url='/admin/login/')
def mapa_racks(request):
    user = request.user
    user_is_senha = user.groups.filter(name="Senha").exists()
    user_is_admin = user.groups.filter(name="Admin").exists()

    # Filtra apenas as empresas do usuário autenticado
    empresas = Empresa.objects.filter(usuarios=user)

    empresa_id = request.GET.get('empresa', None)  # Filtragem por empresa
    pop_id = request.GET.get('pop', None)  # Filtragem por POP

    # Filtrando os POPs relacionados à empresa
    pops = Pop.objects.all()
    if empresa_id:
        pops = pops.filter(empresa__id=empresa_id)

    racks_query = Rack.objects.prefetch_related('equipamentos')
    if empresa_id:
        racks_query = racks_query.filter(pop__empresa__id=empresa_id)
    if pop_id:
        racks_query = racks_query.filter(pop_id=pop_id)

    racks = racks_query.all()

    # Estrutura para armazenar os racks e seus equipamentos
    racks_data = []

    for rack in racks:
        equipamentos = [
            {
                'id': rack_equip.equipamento.id,
                'nome': rack_equip.equipamento.nome,
                'u_inicio': rack_equip.us_inicio,
                'u_fim': rack_equip.us_fim,
                'lado': rack_equip.lado,
            }
            for rack_equip in rack.equipamentos.all()
        ]

        racks_data.append({
            'id': rack.id,
            'nome': rack.nome,
            'pop': rack.pop.nome,
            'us': rack.us,
            'modelo': rack.modelo,
            'observacao': rack.observacao,
            'equipamentos': equipamentos,
        })

    context = {
        'userIsAdmin': user_is_admin,
        'userIsSenha': user_is_senha,
        'empresas': empresas,
        'empresa_id': empresa_id,
        'pops': pops,  # Envia os POPs filtrados
        'racks': racks_data,
    }

    return render(request, 'appisp/mapa_racks.html', context)


# Rota para fornecer os dados do mapa de racks em formato JSON
def mapa_racks_dados(request) -> JsonResponse:
    # Obter os parâmetros de filtro da URL
    empresa_id = request.GET.get('empresa', None)
    pop_id = request.GET.get('pop', None)

    # Filtragem de racks
    racks_query = Rack.objects.prefetch_related('equipamentos__equipamento',
                                                'equipamentos__equipamento__maquinas_virtuais')

    if empresa_id:
        racks_query = racks_query.filter(pop__empresa__id=empresa_id)
    if pop_id:
        racks_query = racks_query.filter(pop_id=pop_id)

    racks = racks_query.all()

    racks_data = []
    for rack in racks:
        equipamentos = [
            {
                'id': equipamento.equipamento.id,
                'nome': equipamento.equipamento.nome,
                'u_inicio': equipamento.us_inicio,
                'u_fim': equipamento.us_fim,
                'lado': equipamento.lado,
                'tipo': equipamento.equipamento.tipo,
                'url_admin': f"/admin/appisp/maquinavirtual/?equipamento__id__exact={equipamento.equipamento.id}&q=",
                'maquinas_virtuais': [vm.nome for vm in equipamento.equipamento.maquinas_virtuais.all()],
            }
            for equipamento in rack.equipamentos.all()
        ]

        racks_data.append({
            'id': rack.id,
            'nome': rack.nome,
            'pop': rack.pop.nome,
            'us': rack.us,
            'modelo': rack.modelo,
            'observacao': rack.observacao,
            'equipamentos': equipamentos,
        })

    # Se uma empresa foi selecionada, buscar os POPs relacionados a essa empresa
    pops_data = []
    if empresa_id:
        pops = Pop.objects.filter(empresa__id=empresa_id)
        pops_data = [{'id': pop.id, 'nome': pop.nome} for pop in pops]

    # Retornar os racks e POPs no formato JSON
    return JsonResponse({'racks': racks_data, 'pops': pops_data})


def atualizar_posicao(request, equipamento_id):
    if request.method == 'POST':
        equipamento = Equipamento.objects.get(id=equipamento_id)

        # Pegando as novas coordenadas do POST
        x_novo = request.POST.get('x')
        y_novo = request.POST.get('y')

        # Atualizando o equipamento
        equipamento.x = float(x_novo)
        equipamento.y = float(y_novo)
        equipamento.save()

        return JsonResponse({"status": "sucesso", "x": x_novo, "y": y_novo})


# View Mapa
@login_required(login_url='/admin/login/')
def mapa(request):
    user = request.user
    user_is_senha = user.groups.filter(name="Senha").exists()
    user_is_admin = user.groups.filter(name="Admin").exists()

    # Filtra apenas as empresas do usuário autenticado
    empresas = Empresa.objects.filter(usuarios=user)

    empresa_id = request.GET.get('empresa', None)  # Pega o parâmetro da empresa na URL

    # Se uma empresa for selecionada, filtramos os equipamentos dela
    equipamentos_query = Equipamento.objects.prefetch_related('portas__conexao')

    if empresa_id:
        equipamentos_query = equipamentos_query.filter(empresa__id=empresa_id)

    equipamentos = equipamentos_query.all()

    # Criando a estrutura de dados para o mapa
    nodes = []
    links = []

    for equipamento in equipamentos:
        # Adicionando os nós (equipamentos)
        nodes.append({
            'id': equipamento.id,
            'nome': equipamento.nome,
            'ip': equipamento.ip,
            'usuario': equipamento.usuario,
            'senha': equipamento.senha,
            'porta': equipamento.porta,
            'protocolo': equipamento.protocolo,
            'status': equipamento.status,  # Status do equipamento
            'empresa': equipamento.empresa.id,  # ID da empresa para filtrar
            'x': equipamento.x,  # Posição X no mapa
            'y': equipamento.y,  # Posição Y no mapa
            'tipo': equipamento.tipo,  # Tipo do equipamento (switch, roteador, etc)
        })

        # Adicionando as conexões entre portas
        for porta in equipamento.portas.all():
            if porta.conexao:
                links.append({
                    'source': porta.equipamento.id,
                    'target': porta.conexao.equipamento.id,
                    'porta_origem': porta.nome,
                    'porta_origem_id': porta.id,  # 👈 AQUI
                    'porta_destino': porta.conexao.nome,
                    'porta_destino_id': porta.conexao.id,  # 👈 E AQUI
                    'tipo': porta.tipo,
                    'speed': porta.speed,
                    'Obs': porta.observacao,
                })

    # Contexto para enviar para o template
    context = {
        'userIsAdmin': user_is_admin,
        'user_is_senha': user_is_senha,
        'empresas': empresas,
        'empresa_id': empresa_id,
        'nodes': nodes,  # Passando nodes (equipamentos) para o JS
        'links': links,  # Passando links (conexões) para o JS
    }

    return render(request, 'appisp/mapa.html', context)


# Rota para retornar os dados em formato JSON
def mapa_dados(request) -> JsonResponse:
    # Busca os equipamentos e prefetch das portas e conexões
    equipamentos = Equipamento.objects.prefetch_related(
        Prefetch('portas', queryset=Porta.objects.select_related('conexao__equipamento'))
    ).all()

    # Inicializa as listas de nodes e links
    nodes = []
    links = []

    # Itera pelos equipamentos para construir os nodes e links
    for equipamento in equipamentos:
        # Adiciona informações do equipamento ao nó
        nodes.append({
            'id': equipamento.id,
            'nome': equipamento.nome,
            'ip': equipamento.ip,
            # Remova 'usuario' e 'senha' se forem sensíveis
            'usuario': equipamento.usuario,
            'senha': equipamento.senha,
            'porta': equipamento.porta,
            'protocolo': equipamento.protocolo,
            'status': equipamento.status,
            'empresa': equipamento.empresa.id,
            'x': equipamento.x,
            'y': equipamento.y,
            'tipo': equipamento.tipo,
        })

        # Adiciona informações de conexões ao link
        for porta in equipamento.portas.all():
            if porta.conexao and porta.conexao.equipamento:
                links.append({
                    'source': porta.equipamento.id,
                    'target': porta.conexao.equipamento.id,
                    "nome_origem": porta.nome,
                    "nome_destino": porta.conexao.nome if porta.conexao else None,
                    'tipo': porta.tipo,
                    'speed': porta.speed,
                })

    # Retorna o JSON com os dados
    return JsonResponse({'nodes': nodes, 'links': links})


class EquipamentoAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Equipamento.objects.none()

        qs = Equipamento.objects.all()

        # Filtrar por empresa passada no formulário
        empresa = self.forwarded.get('empresa', None)
        if empresa:
            qs = qs.filter(empresa=empresa)
        return qs


class PortaAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Porta.objects.none()

        qs = Porta.objects.all()

        # Filtrar apenas as portas dos equipamentos das empresas do usuário
        if not self.request.user.is_superuser:
            qs = qs.filter(equipamento__empresa__usuarios=self.request.user)

        # Filtrar por empresa passada no formulário
        empresa = self.forwarded.get('empresa', None)
        if empresa:
            qs = qs.filter(equipamento__empresa=empresa)

        # Filtrar também pelo "Equipamento de Conexão"
        equipamento_conexao = self.forwarded.get('equipamento_conexao', None)
        if equipamento_conexao:
            qs = qs.filter(equipamento=equipamento_conexao)

        return qs


def get_equipamentos_por_empresa(request):
    empresa_id = request.GET.get('empresa_id')
    equipamentos = Equipamento.objects.filter(empresa_id=empresa_id).values('id', 'nome')

    return JsonResponse(list(equipamentos), safe=False)


def visualizar_vlans_por_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(Equipamento, id=equipamento_id)
    vlans = VlanPorta.objects.filter(porta__equipamento=equipamento)

    return render(request, 'appisp/vlan_por_equipamento.html', {'equipamento': equipamento, 'vlans': vlans})


@login_required
def relatorio_vlans(request):
    usuario = request.user  # Usuário logado
    empresas = Empresa.objects.filter(usuarios=usuario)  # Empresas do usuário
    empresa_id = request.GET.get("empresa")  # Empresa selecionada no filtro

    vlans_por_empresa = {}  # Dicionário vazio para VLANs

    if empresa_id:
        empresa_selecionada = empresas.filter(id=empresa_id).first()
        if empresa_selecionada:
            vlans_por_empresa[empresa_selecionada.nome] = Vlan.objects.filter(empresa=empresa_selecionada)

    return render(request, 'appisp/relatorio_vlans.html', {
        'empresas': empresas,
        'empresa_id': empresa_id,
        'vlans_por_empresa': vlans_por_empresa,
    })


def get_map_data(request):
    equipamentos = Equipamento.objects.all()
    portas = Porta.objects.all()

    nodes = [
        {
            "id": e.id,
            "nome": e.nome,
            "empresa": e.empresa.id,
            "x": e.x,
            "y": e.y,
            "tipo": e.tipo,
            "status": e.status,
        }
        for e in equipamentos
    ]

    links = [
        {
            "source": porta.equipamento.id,
            "target": porta.conexao.equipamento.id,
            "porta_origem": porta.nome,
            "porta_destino": porta.conexao.nome,
            "tipo": porta.tipo,
            "speed": porta.speed,
            "Obs": porta.observacao,
        }
        for porta in portas if porta.conexao and porta.equipamento and porta.conexao.equipamento
    ]

    return JsonResponse({"nodes": nodes, "links": links})


@login_required
def alertas_vlans(request):
    usuario = request.user  # Usuário logado

    # Filtra as empresas associadas ao usuário logado
    empresas = Empresa.objects.filter(usuarios=usuario)

    # Obtém o ID da empresa selecionada no filtro
    empresa_id = request.GET.get("empresa")

    # Inicia a variável vazia (nenhuma VLAN carregada por padrão)
    vlans_sem_porta = None

    # Se uma empresa foi selecionada, carregue as VLANs filtradas
    if empresa_id:
        vlans_sem_porta = Vlan.objects.filter(vlan_portas__isnull=True, empresa_id=empresa_id)

    return render(request, 'appisp/alertas_vlans.html', {
        'vlans_sem_porta': vlans_sem_porta,
        'empresas': empresas,
        'empresa_id': empresa_id,
    })

@login_required
def lista_empresas_json(request):
    empresas = Empresa.objects.filter(usuarios=request.user)  # Supondo uma relação ManyToMany
    empresas_json = [{"id": emp.id, "nome": emp.nome} for emp in empresas]
    return JsonResponse({"empresas": empresas_json})


def lista_vlans_json(request):
    empresa_id = request.GET.get('empresa_id')
    vlans = Vlan.objects.all()
    if empresa_id:
        vlans = vlans.filter(empresa_id=empresa_id)

    data = {"vlans": list(vlans.values("id", "numero", "nome", "empresa_id"))}
    return JsonResponse(data)


def mapa_vlans_json(request):
    empresa_id = request.GET.get("empresa_id")
    vlan_id = request.GET.get("vlan_id")  # Obtém a VLAN selecionada

    equipamentos = Equipamento.objects.all()
    if empresa_id:
        equipamentos = equipamentos.filter(empresa_id=empresa_id)

    equipamentos_data = []

    for equip in equipamentos:
        vlan_portas = VlanPorta.objects.filter(equipamento=equip)

        if vlan_id:
            vlan_portas = vlan_portas.filter(vlan_id=vlan_id)

        # Agrupar portas por VLAN
        vlan_dict = {}
        for vp in vlan_portas:
            vlan_nome = vp.vlan.numero  # Ou vp.vlan.nome, dependendo do que você quer exibir
            if vlan_nome not in vlan_dict:
                vlan_dict[vlan_nome] = []
            vlan_dict[vlan_nome].append(vp.porta.nome)

        vlans = [{"vlan": vlan, "portas": portas} for vlan, portas in vlan_dict.items()]

        if vlans:
            equipamentos_data.append({
                "equipamento": equip.nome,
                "vlans": vlans
            })

    return JsonResponse({"equipamentos": equipamentos_data})


def detalhes_bloco(request, bloco_id):
    bloco = BlocoIP.objects.get(id=bloco_id)

    # Buscar sub-blocos diretamente ligados a esse bloco
    sub_blocos = BlocoIP.objects.filter(parent=bloco)

    # Criar uma lista para armazenar dados dos sub-blocos e seus respectivos IPs
    blocos_com_ips = []
    for sub_bloco in sub_blocos:
        ips = EnderecoIP.objects.filter(bloco=sub_bloco).values(
            'id', 'ip', 'equipamento__nome', 'porta__nome', 'next_hop', 'is_gateway', 'finalidade'
        )
        blocos_com_ips.append({
            'sub_bloco': sub_bloco.bloco_cidr,
            'descricao': sub_bloco.descricao or 'N/A',
            'equipamento': sub_bloco.equipamento.nome if sub_bloco.equipamento else 'N/A',
            'ips': list(ips)  # Lista de IPs associados ao sub-bloco (pode ser vazia)
        })

    return render(request, 'seu_template.html', {
        'bloco': bloco,
        'blocos_com_ips': blocos_com_ips  # Passa a lista para o template
    })


def get_sub_blocos(request, bloco_id):
    sub_blocos = BlocoIP.objects.filter(parent_id=bloco_id).select_related("parent", "equipamento").values(
        'id', 'bloco_cidr', 'tipo_ip', 'parent__bloco_cidr', 'equipamento__nome', 'descricao'
    )
    # Adiciona uma chave "ips" vazia para os sub-blocos sem IPs
    for sub_bloco in sub_blocos:
        ips = EnderecoIP.objects.filter(bloco_id=sub_bloco['id']).values("id", "ip", "equipamento__nome", "porta__nome", "next_hop", "is_gateway", 'finalidade')
        sub_bloco['ips'] = list(ips)  # Lista de IPs associada ao sub-bloco

    return JsonResponse({'sub_blocos': list(sub_blocos)})



def listar_ips_por_bloco(request, bloco_id):
    """Retorna os IPs cadastrados dentro de um bloco específico."""
    ips = EnderecoIP.objects.filter(bloco_id=bloco_id).values("id", "ip", "equipamento__nome", "porta__nome",
                                                              "next_hop", "is_gateway", 'finalidade')
    return JsonResponse({"ips": list(ips)})

def dados_hierarquicos(request, bloco_id):
    try:
        bloco = BlocoIP.objects.get(id=bloco_id)
        sub_blocos = BlocoIP.objects.filter(parent=bloco)

        dados = {
            'bloco': bloco.bloco_cidr,
            'sub_blocos': []
        }

        for sub_bloco in sub_blocos:

            ips = EnderecoIP.objects.filter(bloco=sub_bloco).values(
                "id", "ip", "equipamento__nome", "porta__nome",
                "next_hop", "is_gateway", 'finalidade'
            )

            sub_dados = {
                'sub_bloco': sub_bloco.bloco_cidr,
                'descricao': sub_bloco.descricao or 'N/A',
                'equipamento': sub_bloco.equipamento.nome if sub_bloco.equipamento else 'N/A',
                'ips': list(ips)
            }

            dados['sub_blocos'].append(sub_dados)


        return JsonResponse(dados)

    except BlocoIP.DoesNotExist:
        print("❌ Bloco não encontrado")
        return JsonResponse({'error': 'Bloco não encontrado'}, status=404)


def estrutura_bloco(request, bloco_id):
    # Função recursiva para montar a hierarquia
    def montar_hierarquia(bloco):
        # Buscar os sub-blocos do bloco atual
        sub_blocos = BlocoIP.objects.filter(parent=bloco)

        # Buscar os IPs associados a esse bloco
        ips = EnderecoIP.objects.filter(bloco=bloco).values("id", "ip", "equipamento__nome", "porta__nome", "next_hop", "is_gateway", 'finalidade')

        # Montar o dicionário com os dados
        return {
            "bloco": bloco.bloco_cidr,  # CIDR do bloco
            "sub_blocos": [montar_hierarquia(sb) for sb in sub_blocos],  # Recursivamente monta os sub-blocos
            "ips": list(ips) if ips else []  # Lista de IPs ou uma lista vazia se não houver IPs
        }

    try:
        # Recupera o BlocoIP com base no id
        bloco = BlocoIP.objects.get(id=bloco_id)

        # Monta a hierarquia do bloco
        estrutura = montar_hierarquia(bloco)

        # Retorna a estrutura em formato JSON
        return JsonResponse(estrutura)

    except BlocoIP.DoesNotExist:
        # Caso o bloco com o id fornecido não seja encontrado
        return JsonResponse({'error': 'Bloco não encontrado'}, status=404)


@staff_member_required
def testar_conexao(request, pk):
    integracao = get_object_or_404(IntegracaoZabbix, pk=pk)
    payload = {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
            "user": integracao.usuario,
            "password": integracao.senha
        },
        "id": 1
    }
    try:
        response = requests.post(integracao.url, json=payload, timeout=5)
        data = response.json()
        if 'result' in data:
            messages.success(request, "✅ Conexão com Zabbix bem-sucedida!")
        else:
            messages.error(request, f"❌ Falha na autenticação com o Zabbix: {data.get('error')}")
    except Exception as e:
        messages.warning(request, f"⚠️ Erro ao conectar: {str(e)}")

    return redirect(reverse('admin:appisp_integracaozabbix_change', args=[pk]))

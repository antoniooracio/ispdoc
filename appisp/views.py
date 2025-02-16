from django import forms
from django.contrib.auth.models import User
from dal import autocomplete
from django.http import JsonResponse
from django.db.models import Prefetch
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from .models import Equipamento, Porta, Empresa, Pop, Rack, Equipamento, BlocoIP, EnderecoIP, VlanPorta, Vlan
from .forms import PortaForm, EnderecoIPForm


def detalhes_bloco(request, bloco_id):
    bloco = BlocoIP.objects.get(id=bloco_id)

    # Buscar sub-blocos diretamente ligados a esse bloco
    sub_blocos = BlocoIP.objects.filter(parent=bloco)

    # Criar um dicionário para armazenar IPs dentro de cada sub-bloco
    blocos_com_ips = {sub_bloco: EnderecoIP.objects.filter(bloco=sub_bloco) for sub_bloco in sub_blocos}

    return render(request, 'seu_template.html', {
        'bloco': bloco,
        'blocos_com_ips': blocos_com_ips
    })


def get_sub_blocos(request, bloco_id):
    sub_blocos = BlocoIP.objects.filter(parent_id=bloco_id).select_related("parent", "equipamento").values(
        'id', 'bloco_cidr', 'tipo_ip', 'parent__bloco_cidr', 'equipamento__nome', 'descricao'
    )
    return JsonResponse({'sub_blocos': list(sub_blocos)})


def listar_ips_por_bloco(request, bloco_id):
    """Retorna os IPs cadastrados dentro de um bloco específico."""
    ips = EnderecoIP.objects.filter(bloco_id=bloco_id).values("id", "ip", "equipamento__nome", "porta__nome",
                                                              "next_hop", "is_gateway", 'finalidade')
    return JsonResponse({"ips": list(ips)})


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
    user_is_admin = request.user.groups.filter(name="Admin").exists()

    empresas = Empresa.objects.all()
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
    user_is_admin = request.user.groups.filter(name="Admin").exists()

    empresas = Empresa.objects.all()
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
                    'source': porta.equipamento.id,  # Equipamento de origem
                    'target': porta.conexao.equipamento.id,  # Equipamento de destino
                    'porta_origem': porta.nome,  # Nome da porta de origem
                    'porta_destino': porta.conexao.nome,  # Nome da porta de destino
                    'tipo': porta.tipo,  # Tipo da conexão (Fibra, Elétrico, etc.)
                    'speed': porta.speed,  # Velocidade da porta (100M, 1G, etc.)
                    'Obs': porta.observacao,  # Observação da porta
                })

    # Contexto para enviar para o template
    context = {
        'userIsAdmin': user_is_admin,
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

        return qs


def get_equipamentos_por_empresa(request):
    empresa_id = request.GET.get('empresa_id')
    equipamentos = Equipamento.objects.filter(empresa_id=empresa_id).values('id', 'nome')

    return JsonResponse(list(equipamentos), safe=False)


def visualizar_vlans_por_equipamento(request, equipamento_id):
    equipamento = get_object_or_404(Equipamento, id=equipamento_id)
    vlans = VlanPorta.objects.filter(porta__equipamento=equipamento)

    return render(request, 'appisp/vlan_por_equipamento.html', {'equipamento': equipamento, 'vlans': vlans})


def mapa_vlans_json(request):
    empresa_id = request.GET.get("empresa_id")  # Obtém a empresa selecionada

    # Filtra os equipamentos da empresa selecionada
    if empresa_id:
        equipamentos = Equipamento.objects.filter(empresa_id=empresa_id)
    else:
        equipamentos = Equipamento.objects.all()

    equipamentos_data = []

    for equip in equipamentos:
        vlan_portas = VlanPorta.objects.filter(equipamento=equip)
        vlans = [{"vlan": vp.vlan.numero, "porta": vp.porta.nome} for vp in vlan_portas]

        equipamentos_data.append({
            "equipamento": equip.nome,
            "vlans": vlans
        })

    return JsonResponse({"equipamentos": equipamentos_data})


def relatorio_vlans(request):
    vlans = Vlan.objects.all().select_related('empresa')
    vlans_por_empresa = {}

    for vlan in vlans:
        if vlan.empresa.nome not in vlans_por_empresa:
            vlans_por_empresa[vlan.empresa.nome] = []
        vlans_por_empresa[vlan.empresa.nome].append(vlan)

    return render(request, 'appisp/relatorio_vlans.html', {'vlans_por_empresa': vlans_por_empresa})


def alertas_vlans(request):
    vlans_sem_porta = Vlan.objects.filter(vlan_portas__isnull=True)

    return render(request, 'appisp/alertas_vlans.html', {'vlans_sem_porta': vlans_sem_porta})


def lista_empresas_json(request):
    empresas = list(Empresa.objects.values("id", "nome"))
    return JsonResponse({"empresas": empresas})
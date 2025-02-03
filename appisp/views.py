from django.shortcuts import render
from dal import autocomplete
from django.http import JsonResponse
from .models import Equipamento, Porta, Empresa
from django.db.models import Prefetch
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

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
                    'source': porta.equipamento.id,         # Equipamento de origem
                    'target': porta.conexao.equipamento.id, # Equipamento de destino
                    'porta_origem': porta.nome,             # Nome da porta de origem
                    'porta_destino': porta.conexao.nome,    # Nome da porta de destino
                    'tipo': porta.tipo,                     # Tipo da conexão (Fibra, Elétrico, etc.)
                    'speed': porta.speed,                   # Velocidade da porta (100M, 1G, etc.)
                    'Obs': porta.observacao,                # Observação da porta
                })

    # Contexto para enviar para o template
    context = {
        'empresas': empresas,  # Enviando as empresas para o template
        'nodes': nodes,        # Dados dos equipamentos (nodes) para o JS
        'links': links,        # Links de conexão entre equipamentos para o JS
    }

    #print("Nodes:", nodes)
    #print("Links:", links)

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

        # Filtrar por empresa passada no formulário
        empresa = self.forwarded.get('empresa', None)
        if empresa:
            qs = qs.filter(equipamento__empresa=empresa)
        return qs

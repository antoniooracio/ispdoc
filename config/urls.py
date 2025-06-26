"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from appisp.admin import admin_site
from django.http import JsonResponse
from django.views.generic.base import TemplateView
from django.urls import path, include
from django.shortcuts import render
from appisp.views import (EquipamentoAutocomplete, PortaAutocomplete, mapa, atualizar_posicao, mapa_racks,
                          mapa_racks_dados, get_equipamentos_por_empresa, adicionar_endereco_ip, listar_ips_por_bloco,
                          get_sub_blocos, visualizar_vlans_por_equipamento, mapa_vlans_json, relatorio_vlans,
                          alertas_vlans, lista_empresas_json, lista_vlans_json, estrutura_bloco, estrutura_bloco, get_portas,
                          verificar_status_equipamentos, listar_equipamentosApi, atualizar_status_equipamento, get_map_data,
                          get_equipamento, api_portas, conectar_portas, desconectar_portas, testar_conexao, listar_blocos_ip_api
                          )
from appisp.models import Porta
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static

@login_required
def get_portas_por_equipamento(request, equipamento_id):
    portas = Porta.objects.filter(equipamento_id=equipamento_id)
    portas_data = [{'id': porta.id, 'nome': porta.nome} for porta in portas]
    return JsonResponse({'portas': portas_data})


@login_required
def mapa_vlans(request):
    return render(request, 'appisp/mapa_vlans.html')


urlpatterns = [
    path('admin/', admin_site.urls),
    path('equipamento-autocomplete/', EquipamentoAutocomplete.as_view(), name='equipamento-autocomplete'),
    path('porta-autocomplete/', PortaAutocomplete.as_view(), name='porta-autocomplete'),
    path('mapa-rede/', mapa, name='mapa-rede'),  # Adicionando a URL para a página do mapa
    path('atualizar_posicao/<int:equipamento_id>/', atualizar_posicao, name='atualizar_posicao'),
    path('mapa-rack/', mapa_racks, name='mapa_rack'),
    path('mapa-rack/dados/', mapa_racks_dados, name='mapa_rack_dados'),
    path('get-equipamentos/', get_equipamentos_por_empresa, name='get-equipamentos'),
    path("get-portas/", get_portas, name="get-portas"),
    path('api/portas', api_portas, name='api_portas'),
    path('api/conectar-portas/', conectar_portas, name='conectar-portas'),
    path('api/desconectar-portas/', desconectar_portas, name='desconectar-portas'),
    path('api/blocos-ip/', listar_blocos_ip_api, name='api_listar_blocos_ip'),
    path('endereco_ip/', adicionar_endereco_ip, name='endereco_ip'),
    path('equipamento/<int:equipamento_id>/vlans/', visualizar_vlans_por_equipamento, name='vlans_por_equipamento'),
    path('mapa_vlans/', mapa_vlans, name='mapa_vlans'),
    path('mapa_vlans_json/', mapa_vlans_json, name='mapa_vlans_json'),
    path('relatorio_vlans/', relatorio_vlans, name='relatorio_vlans'),
    path('alertas_vlans/', alertas_vlans, name='alertas_vlans'),
    path('ajax/portas_por_equipamento/<int:equipamento_id>/', get_portas_por_equipamento,
         name='portas_por_equipamento'),
    path('testar-conexao/<int:pk>/', testar_conexao, name='testar_conexao'),

    path("ajax/ips_por_bloco/<int:bloco_id>/", listar_ips_por_bloco, name="listar_ips_por_bloco"),
    path('ajax/sub_blocos_por_bloco/<int:bloco_id>/', get_sub_blocos, name='ajax_sub_blocos_por_bloco'),
    path("lista_empresas_json/", lista_empresas_json, name="lista_empresas_json"),
    path('lista_vlans_json', lista_vlans_json, name='lista_vlans_json'),
    path('ajax/dados_hierarquicos/<int:bloco_id>/', estrutura_bloco, name='dados_hierarquicos'),
    path('ajax/estrutura_bloco/<int:bloco_id>/', estrutura_bloco, name='estrutura_bloco'),
    path('', TemplateView.as_view(template_name='index.html'), name='index'),
    path('verificar_status/', verificar_status_equipamentos, name='verificar_status'),
    path("api/listar_equipamentosapi/", listar_equipamentosApi, name="listar_equipamentosapi"),
    path('api/atualizar_status/<int:equipamento_id>/', atualizar_status_equipamento, name="atualizar_status_equipamento"),
    path('api/get_map_data/', get_map_data, name="atualizar_mapa"),
    path('api/equipamento/<int:equipamento_id>/', get_equipamento, name='get_equipamento'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

import json

from django.template.response import TemplateResponse
from django.utils import timezone
import requests
import re
from django.contrib import admin, messages
from django import forms
from django.urls import path
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.admin import AdminSite
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect, JsonResponse
from .forms import PortaForm, RackForm, RackEquipamentoForm, EnderecoIPForm, MaquinaVirtualForm, EquipamentoForm, \
    EnderecoIPForm, CadastrarEnderecosForm, ModeloForm
from .views import mapa, mapa_racks
from django.contrib.admin import SimpleListFilter
from .models import Empresa, Pop, Fabricante, Modelo, Equipamento, Porta, BlocoIP, EnderecoIP, Rack, RackEquipamento, \
    MaquinaVirtual, Disco, Rede, Vlan, VlanPorta, EmpresaToken, IntegracaoZabbix, IntegracaoNetbox, Interface
import ipaddress
from django.utils.html import format_html
from django.contrib import admin
from ipaddress import ip_network
from django.core.exceptions import ValidationError

class PopEmpresaFilter(SimpleListFilter):
    title = "Pop"
    parameter_name = "pop"

    def lookups(self, request, model_admin):
        """ Lista apenas os Pops das empresas do usuário """
        if request.user.is_superuser:
            return [(pop.id, pop.nome) for pop in Pop.objects.all()]

        pops_usuario = Pop.objects.filter(empresa__usuarios=request.user)
        return [(pop.id, pop.nome) for pop in pops_usuario]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(pop_id=self.value())
        return queryset


class RackEmpresaFilter(SimpleListFilter):
    title = "Rack"
    parameter_name = "rack"

    def lookups(self, request, model_admin):
        """ Lista apenas os Racks das empresas do usuário """
        if request.user.is_superuser:
            return [(rack.id, rack.nome) for rack in Rack.objects.all()]

        racks_usuario = Rack.objects.filter(empresa__usuarios=request.user)
        return [(rack.id, rack.nome) for rack in racks_usuario]

    def queryset(self, request, queryset):
        """ Filtra os equipamentos pelo Rack selecionado """
        if self.value():
            return queryset.filter(rack_id=self.value())
        return queryset


class DiscoInline(admin.TabularInline):  # Ou admin.StackedInline para exibição vertical
    model = Disco
    extra = 1  # Número inicial de campos exibidos


class RedeInline(admin.TabularInline):
    model = Rede
    extra = 1  # Número inicial de campos exibidos


class EnderecoIPEmpresaFilter(SimpleListFilter):
    """Filtro para exibir apenas os IPs dos equipamentos da empresa do usuário"""
    title = "Empresa"
    parameter_name = "empresa"

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            empresas = Empresa.objects.all()
        else:
            empresas = request.user.empresas.all()

        return [(empresa.id, empresa.nome) for empresa in empresas]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(equipamento__empresa_id=self.value())  # Filtrar por empresa
        return queryset


class EquipamentoEmpresaFilter(SimpleListFilter):
    """Filtro personalizado para exibir apenas equipamentos das empresas do usuário"""
    title = "Equipamento"
    parameter_name = "equipamento"

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            equipamentos = Equipamento.objects.all()
        else:
            equipamentos = Equipamento.objects.filter(empresa__usuarios=request.user)

        return [(equip.id, equip.nome) for equip in equipamentos]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(equipamento_id=self.value())  # Usar equipamento_id diretamente
        return queryset


class VlanPortaFilter(SimpleListFilter):
    """Filtro personalizado para exibir apenas portas das empresas do usuário"""
    title = "Vlan"
    parameter_name = "numero"

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            vlans = Vlan.objects.all()
        else:
            vlans = Vlan.objects.filter(empresa__usuarios=request.user)

        return [(vlan.id, f"{vlan.numero} - {vlan.nome}") for vlan in vlans]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(vlan_id=self.value())  # Usar vlan_id diretamente
        return queryset


class EquipamentoPortaFilter(SimpleListFilter):
    """Filtro personalizado para exibir apenas portas das empresas do usuário"""
    title = "Porta"
    parameter_name = "nome"

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            portas = Porta.objects.all()
        else:
            portas = Porta.objects.filter(empresa__usuarios=request.user)

        return [(porta.id, porta.nome) for porta in portas]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(porta_id=self.value())  # Usar porta_id diretamente
        return queryset


class EmpresaUsuarioFilter(SimpleListFilter):
    """Filtro personalizado para exibir apenas empresas às quais o usuário pertence"""
    title = "Empresa"
    parameter_name = "empresa"

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            empresas = Empresa.objects.all()
        else:
            empresas = request.user.empresas.all()

        return [(empresa.id, empresa.nome) for empresa in empresas]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(equipamento__empresa_id=self.value())  # Filtrar corretamente pela empresa
        return queryset


class BlocoEmpresaFilter(SimpleListFilter):
    """Filtro para exibir apenas os blocos de IP pertencentes à empresa do usuário"""
    title = "Bloco de IP"
    parameter_name = "bloco"

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            blocos = BlocoIP.objects.all()
        else:
            blocos = BlocoIP.objects.filter(empresa__usuarios=request.user)

        return [(bloco.id, bloco.bloco_cidr) for bloco in blocos]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(bloco_id=self.value())  # Filtra os IPs do bloco selecionado
        return queryset


class PopUsuarioFilter(SimpleListFilter):
    title = "POP"
    parameter_name = "pop"

    def lookups(self, request, model_admin):
        """ Lista apenas os POPs das empresas do usuário """
        if request.user.is_superuser:
            return [(pop.id, pop.nome) for pop in model_admin.get_queryset(request).values_list('id', 'nome')]

        pops_usuario = Pop.objects.filter(empresa__usuarios=request.user)
        return [(pop.id, pop.nome) for pop in pops_usuario]

    def queryset(self, request, queryset):
        """ Filtra os equipamentos pelo POP selecionado """
        if self.value():
            return queryset.filter(pop_id=self.value())
        return queryset


@admin.register(Vlan)
class VlanAdmin(admin.ModelAdmin):
    list_display = ('numero', 'nome', 'empresa', 'equipamento', 'tipo', 'status')
    list_filter = ('empresa', 'tipo', 'status')
    search_fields = ('numero', 'nome', 'empresa__nome')

    class Media:
        js = ('js/vlan_dependente.js',)

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ('empresa', 'equipamento')
        return (EmpresaUsuarioFilter, EquipamentoEmpresaFilter)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(empresa__usuarios=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'equipamento' and request.GET.get('empresa'):
            empresa_id = request.GET.get('empresa')
            kwargs["queryset"] = Equipamento.objects.filter(empresa_id=empresa_id)

        if not request.user.is_superuser:
            if db_field.name == "empresa":
                kwargs["queryset"] = Empresa.objects.filter(usuarios=request.user)
            elif db_field.name == "equipamento":
                kwargs["queryset"] = Equipamento.objects.filter(empresa__usuarios=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(VlanPorta)
class VlanPortaAdmin(admin.ModelAdmin):
    list_display = ('vlan', 'porta', 'get_equipamento', 'tipo', 'vlan_nativa')
    list_filter = (EmpresaUsuarioFilter, EquipamentoEmpresaFilter, EquipamentoPortaFilter, VlanPortaFilter)

    class Media:
        js = ('js/vlan_dependente.js',)

    change_list_template = "admin/vlan_changelist.html"  # Personalizamos o template

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        # Filtra apenas VLANs, Equipamentos e Portas da empresa do usuário
        return qs.filter(
            vlan__empresa__usuarios=request.user
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Restringe as escolhas de VLAN, Porta e Equipamento conforme a empresa do usuário.
        """
        if db_field.name == 'equipamento' and request.GET.get('empresa'):
            empresa_id = request.GET.get('empresa')
            kwargs["queryset"] = Equipamento.objects.filter(empresa_id=empresa_id)

        if db_field.name == 'porta' and request.GET.get('equipamento'):
            equipamento_id = request.GET.get('equipamento')
            kwargs["queryset"] = Equipamento.objects.filter(equipamento_id=equipamento_id)

        if not request.user.is_superuser:
            if db_field.name == "vlan":
                kwargs["queryset"] = Vlan.objects.filter(empresa__usuarios=request.user)
            elif db_field.name == "porta":
                kwargs["queryset"] = Porta.objects.filter(equipamento__empresa__usuarios=request.user)
            elif db_field.name == "empresa":
                kwargs["queryset"] = Empresa.objects.filter(usuarios=request.user)
            elif db_field.name == "equipamento":
                kwargs["queryset"] = Equipamento.objects.filter(empresa__usuarios=request.user)
            elif db_field.name == "vlan":
                kwargs["queryset"] = Vlan.objects.filter(empresa__usuarios=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_equipamento(self, obj):
        return obj.porta.equipamento.nome  # Obtém o nome do equipamento associado à porta


@admin.register(MaquinaVirtual)
class MaquinaVirtualAdmin(admin.ModelAdmin):
    form = MaquinaVirtualForm
    list_display = ('nome', 'empresa', 'equipamento', 'sistema_operacional', 'tipo_acesso')
    search_fields = ('nome', 'empresa__nome', 'equipamento__nome', 'sistema_operacional')
    list_filter = ('empresa', 'equipamento')
    inlines = [DiscoInline, RedeInline]  # Adiciona os campos de discos e redes no formulário

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class FormWithRequest(Form):
            def __init__(self2, *args, **kwargs2):
                kwargs2['request'] = request
                super().__init__(*args, **kwargs2)

        return FormWithRequest

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['user_is_senha'] = request.user.groups.filter(name='Senha').exists()
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def get_queryset(self, request):
        """ Filtra as máquinas virtuais para que usuários comuns só vejam as da sua empresa """
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            empresas_usuario = request.user.empresas.all()
            return qs.filter(empresa__in=empresas_usuario)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Filtra os campos de chave estrangeira para mostrar apenas dados da empresa do usuário """
        if db_field.name == "empresa":
            if not request.user.is_superuser:
                kwargs["queryset"] = db_field.related_model.objects.filter(usuarios=request.user)
        elif db_field.name == "equipamento":
            if not request.user.is_superuser:
                empresas_usuario = request.user.empresas.all()
                kwargs["queryset"] = db_field.related_model.objects.filter(empresa__in=empresas_usuario, tipo="VMWARE")
            else:
                kwargs["queryset"] = db_field.related_model.objects.filter(tipo="VMWARE")

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_search_results(self, request, queryset, search_term):
        """ Filtra os resultados da pesquisa para usuários comuns """
        queryset, use_distinct = super().get_search_results(request, queryset, search_term)
        if not request.user.is_superuser:
            empresas_usuario = request.user.empresas.all()
            queryset = queryset.filter(empresa__in=empresas_usuario)
        return queryset, use_distinct

    def get_list_filter(self, request):
        """Aplica os filtros personalizados para exibir apenas dados acessíveis ao usuário"""
        if request.user.is_superuser:
            return (EmpresaUsuarioFilter, EquipamentoEmpresaFilter)  # Superusuário vê tudo

        return (EmpresaUsuarioFilter, EquipamentoEmpresaFilter)  # Usuário comum vê apenas os dados acessíveis


# Adicionando uma TAB no Rack para mostrar os equipamentos
class RackEquipamentoInline(admin.TabularInline):
    model = RackEquipamento
    fields = ('equipamento', 'us_inicio', 'us_fim', 'lado')
    readonly_fields = ('equipamento', 'us_inicio', 'us_fim', 'lado')
    can_delete = False
    extra = 0
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    form = RackForm  # Usa o formulário com validação
    list_display = ('nome', 'pop', 'empresa', 'us', 'modelo')
    list_filter = ('empresa', 'pop')
    search_fields = ('nome', 'pop__nome', 'empresa__nome')
    ordering = ('empresa', 'pop', 'nome')
    inlines = [RackEquipamentoInline]

    def get_queryset(self, request):
        """ Lista apenas os racks das empresas do usuário """
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            empresas_usuario = request.user.empresas.all()
            return qs.filter(empresa__in=empresas_usuario)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Filtra os POPs e Empresas disponíveis no cadastro do Rack """
        if not request.user.is_superuser:
            empresas_usuario = request.user.empresas.all()
            if db_field.name == "empresa":
                kwargs["queryset"] = db_field.related_model.objects.filter(id__in=empresas_usuario)
            elif db_field.name == "pop":
                kwargs["queryset"] = db_field.related_model.objects.filter(empresa__in=empresas_usuario)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_list_filter(self, request):
        """Aplica filtros personalizados de empresa e pop."""
        if request.user.is_superuser:
            return ('pop', 'empresa')  # Superusuário vê tudo

        return (EmpresaUsuarioFilter, PopEmpresaFilter,)  # Usuário comum vê apenas as empresas permitidas


@admin.register(RackEquipamento)
class RackEquipamentoAdmin(admin.ModelAdmin):
    form = RackEquipamentoForm  # Usa o formulário com validação
    list_display = ('rack', 'equipamento', 'us_inicio', 'us_fim', 'lado')
    search_fields = ('rack__nome', 'equipamento__nome')
    ordering = ('rack', 'us_inicio')
    autocomplete_fields = ('rack', 'equipamento')

    change_list_template = "admin/mapa_rack_changelist.html"  # Personalizamos o template

    def get_list_filter(self, request):
        """Aplica filtros personalizados para exibir apenas dados acessíveis ao usuário"""
        if request.user.is_superuser:
            return ('rack', 'lado')  # Superusuário vê tudo

        return (
        EquipamentoEmpresaFilter, RackEmpresaFilter, 'lado')  # Usuário comum vê apenas racks e equipamentos da empresa

    def get_queryset(self, request):
        """ Lista apenas os equipamentos dentro dos racks das empresas do usuário """
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            empresas_usuario = request.user.empresas.all()
            return qs.filter(rack__empresa__in=empresas_usuario)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Filtra Racks e Equipamentos disponíveis no cadastro """
        if not request.user.is_superuser:
            empresas_usuario = request.user.empresas.all()
            if db_field.name == "rack":
                kwargs["queryset"] = db_field.related_model.objects.filter(empresa__in=empresas_usuario)
            elif db_field.name == "equipamento":
                kwargs["queryset"] = db_field.related_model.objects.filter(empresa__in=empresas_usuario)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class LoteForm(forms.Form):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.none(),  # Inicialmente vazio
        required=True,
        label="Empresa",
    )
    nome_base = forms.CharField(label="Nome Base", max_length=100)
    inicio = forms.IntegerField(label="Número Inicial", min_value=0)
    quantidade = forms.IntegerField(label="Quantidade", min_value=1)
    equipamento = forms.ModelChoiceField(
        queryset=Equipamento.objects.none(),  # Inicialmente vazio, será carregado via AJAX
        label="Equipamento",
        required=True
    )
    tipo = forms.ChoiceField(
        choices=Porta.TIPO_CHOICES,
        label="Tipo",
        required=True
    )
    speed = forms.ChoiceField(
        choices=Porta.SPEED_CHOICES,  # Usa as opções de velocidade do modelo
        label="Speed",
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)  # Obtém o request
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.is_authenticated:
            # Filtra as empresas associadas ao usuário logado
            self.fields['empresa'].queryset = Empresa.objects.filter(usuarios=self.request.user)

        empresa_id = self.data.get('empresa') or self.initial.get('empresa')
        if empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
                self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa=empresa)
            except Empresa.DoesNotExist:
                self.fields['equipamento'].queryset = Equipamento.objects.none()
        else:
            self.fields['equipamento'].queryset = Equipamento.objects.none()


# Filtro personalizado para empresa
class EmpresaFilter(SimpleListFilter):
    title = 'Empresa'
    parameter_name = 'empresa'

    def lookups(self, request, model_admin):
        # Retorna uma lista de empresas disponíveis
        empresas = Empresa.objects.all()
        return [(empresa.id, empresa.nome) for empresa in empresas]

    def queryset(self, request, queryset):
        # Filtra as portas com base na empresa selecionada
        if self.value():
            return queryset.filter(equipamento__empresa__id=self.value())
        return queryset


# Melhora o Formulario de Lista de Blocos
class BlocoIPForm(forms.ModelForm):
    class Meta:
        model = BlocoIP
        fields = '__all__'

    def clean_bloco_cidr(self):
        bloco_cidr = self.cleaned_data['bloco_cidr']

        try:
            bloco = ipaddress.ip_network(bloco_cidr, strict=False)  # Verifica se é um bloco válido
        except ValueError:
            raise forms.ValidationError("Formato inválido para um bloco CIDR.")

        return bloco_cidr

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'empresa' in self.data:
            try:
                empresa_id = int(self.data.get('empresa'))
                self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa_id=empresa_id)
                self.fields['parent'].queryset = BlocoIP.objects.filter(empresa_id=empresa_id)  # Filtro para parent
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa=self.instance.empresa)
            self.fields['parent'].queryset = BlocoIP.objects.filter(empresa=self.instance.empresa)  # Filtro para parent


@admin.action(description='Subdividir blocos selecionados')
def subdividir_blocos(modeladmin, request, queryset):
    """
    Subdivide os blocos selecionados em dois sub-blocos.
    """
    total_subdivisoes = 0

    for bloco in queryset:
        # Verifica se o bloco já tem filhos (já foi subdividido)
        if bloco.sub_blocos.exists():
            modeladmin.message_user(request, f"O bloco {bloco.bloco_cidr} já foi subdividido.", level=messages.WARNING)
            continue  # Pula

        try:
            rede = ip_network(bloco.bloco_cidr, strict=False)
            prefixo_atual = rede.prefixlen

            # Impede divisão de /32 (IPv4) e /128 (IPv6)
            if (rede.version == 4 and prefixo_atual >= 32) or (rede.version == 6 and prefixo_atual >= 128):
                modeladmin.message_user(request, f"O bloco {bloco.bloco_cidr} não pode ser subdividido (prefixo máximo).", level=messages.WARNING)
                continue

            novo_prefixo = prefixo_atual + 1  # Sempre divide ao meio

            subnets = list(rede.subnets(new_prefix=novo_prefixo))  # Gera duas sub-redes

            for subrede in subnets:
                BlocoIP.objects.create(
                    empresa=bloco.empresa,
                    bloco_cidr=str(subrede),
                    parent=bloco,
                    tipo_ip=bloco.tipo_ip
                )
                total_subdivisoes += 1

        except Exception as e:
            modeladmin.message_user(request, f"Erro ao subdividir bloco {bloco.bloco_cidr}: {e}", level=messages.ERROR)

    if total_subdivisoes > 0:
        modeladmin.message_user(request, f"{total_subdivisoes} sub-blocos criados com sucesso.", level=messages.SUCCESS)
    else:
        modeladmin.message_user(request, "Nenhum bloco foi subdividido.", level=messages.WARNING)

from django.http import HttpResponseRedirect
from django.urls import reverse

@admin.action(description="Cadastrar Endereços IP no Bloco")
def cadastrar_enderecos(self, request, queryset):
    if queryset.count() != 1:
        self.message_user(request, "Por favor, selecione apenas um bloco para cadastrar endereços.", level=messages.WARNING)
        return

    bloco = queryset.first()
    url = reverse('admin:appisp_blocoip_cadastrar_enderecos', args=[bloco.id])
    return HttpResponseRedirect(url)


# Lista os Blocos Pai e filhos
class BlocoCIDRListFilter(SimpleListFilter):
    title = 'Bloco CIDR'
    parameter_name = 'bloco_cidr'

    def lookups(self, request, model_admin):
        blocos = model_admin.get_queryset(request)
        return [(b.bloco_cidr, b.bloco_cidr) for b in blocos]

    def queryset(self, request, queryset):
        if self.value():
            try:
                rede_busca = ip_network(self.value(), strict=False)
                bloco_pai = queryset.filter(bloco_cidr=str(rede_busca)).first()

                if bloco_pai:
                    blocos_ids = [bloco_pai.id]

                    def coletar_descendentes(bloco):
                        for sub_bloco in bloco.sub_blocos.all():
                            blocos_ids.append(sub_bloco.id)
                            coletar_descendentes(sub_bloco)

                    coletar_descendentes(bloco_pai)

                    return queryset.filter(id__in=blocos_ids)
            except ValueError:
                pass

        return queryset


def carregar_portas(request):
    equipamento_id = request.GET.get('equipamento')
    portas = Porta.objects.filter(equipamento_id=equipamento_id).values('id', 'nome')
    return JsonResponse(list(portas), safe=False)


@admin.register(BlocoIP)
class BlocoIPAdmin(admin.ModelAdmin):
    list_display = (
        'bloco_indented', 'empresa', 'bloco_cidr', 'sub_blocos_count',
        'utilizacao_barra', 'tipo_ip', 'parent', 'gateway', 'acoes_dropdown'
    )
    readonly_fields = ('utilizacao_barra',)
    search_fields = ('bloco_cidr', 'empresa__nome', 'equipamento__nome')
    list_filter = (BlocoCIDRListFilter, 'tipo_ip', 'empresa', 'equipamento', 'parent')
    form = BlocoIPForm
    actions = [subdividir_blocos, cadastrar_enderecos]

    @admin.display(description="Ações")
    def acoes_dropdown(self, obj):
        from django.utils.safestring import mark_safe
        from ipaddress import ip_network
        from django.urls import reverse
        from django.utils.html import format_html

        acoes = []

        # Subdividir, se aplicável
        if not obj.sub_blocos.exists():
            try:
                rede = ip_network(obj.bloco_cidr, strict=False)
                prefixo_atual = rede.prefixlen
                if not ((rede.version == 4 and prefixo_atual >= 32) or (rede.version == 6 and prefixo_atual >= 128)):
                    subdividir_url = reverse('admin:appisp_blocoip_subdividir', args=[obj.id])
                    acoes.append(
                        f'<a href="{subdividir_url}" style="display:block; padding:8px 12px; text-decoration:none; color:#333;">Subdividir</a>')
            except Exception:
                pass

        # Visualizar IPs, se aplicável
        if not obj.sub_blocos.exists():
            visualizar_url = reverse('admin:appisp_blocoip_visualizar_ips', args=[obj.id])
            acoes.append(
                f'<a href="{visualizar_url}" style="display:block; padding:8px 12px; text-decoration:none; background-color: #fff; color:#333;">IPs</a>')

        # Se não tiver ações
        if not acoes:
            return format_html('<span style="color: gray;"></span>')

        # Dropdown estilo Admin
        return format_html('''
            <div style="position: relative; display: inline-block;">
                <button type="button" class="btn btn-outline-success btn-sm" style="
                " onclick="this.nextElementSibling.style.display = this.nextElementSibling.style.display === 'block' ? 'none' : 'block';">
                    ▼
                </button>
                <div style="
                    display: none;
                    position: absolute;
                    background-color: #fff;
                    min-width: 100px;
                    left: -20px;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    box-shadow: 0px 2px 5px rgba(0,0,0,0.2);
                    z-index: 1;
                ">
                    {}
                </div>
            </div>
        ''', mark_safe(''.join(acoes)))

    @admin.display(description='Bloco CIDR')
    def bloco_indented(self, obj):
        indent = '*' * obj.nivel()  # Um asterisco por nível
        return format_html(f'{indent} {obj.bloco_cidr}')

    @admin.display(description='Qtd S-bloco')
    def sub_blocos_count(self, obj):
        def contar_descendentes(bloco):
            count = bloco.sub_blocos.count()
            for sub_bloco in bloco.sub_blocos.all():
                count += contar_descendentes(sub_bloco)
            return count

        return contar_descendentes(obj)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:bloco_id>/subdividir/', self.admin_site.admin_view(self.subdividir_view),
                 name='appisp_blocoip_subdividir'),
            path('<int:bloco_id>/visualizar_ips/', self.admin_site.admin_view(self.visualizar_ips),
                 name='appisp_blocoip_visualizar_ips'),
            path(

                '<int:bloco_id>/cadastrar_enderecos/',
                self.admin_site.admin_view(self.cadastrar_enderecos_view),
                name='appisp_blocoip_cadastrar_enderecos',
            ),
            path('ajax/carregar-portas/', self.admin_site.admin_view(self.carregar_portas_view),
                 name='appisp_blocoip_carregar_portas'),
        ]
        return custom_urls + urls

    def carregar_portas_view(self, request):
        equipamento_id = request.GET.get('equipamento')
        portas = Porta.objects.filter(equipamento_id=equipamento_id).values('id', 'nome')
        return JsonResponse(list(portas), safe=False)

    def cadastrar_enderecos_view(self, request, bloco_id):
        bloco = get_object_or_404(BlocoIP, id=bloco_id)

        # Verifique se o bloco tem filhos (subdividido)
        if bloco.sub_blocos.exists():
            self.message_user(request, 'Este bloco foi subdividido. Cadastre os IPs nos blocos filhos.',
                              level=messages.ERROR)
            return redirect('admin:appisp_blocoip_changelist')  # Redireciona de volta à lista de blocos

        EnderecoForm = CadastrarEnderecosForm

        if request.method == 'POST':
            form = EnderecoForm(request.POST, request=request, user=request.user)
            if form.is_valid():
                equipamento = form.cleaned_data['equipamento']
                porta = form.cleaned_data['porta']
                finalidade = form.cleaned_data.get('finalidade')
                next_hop = form.cleaned_data.get('next_hop')
                is_gateway = form.cleaned_data.get('is_gateway', False)

                rede = ip_network(bloco.bloco_cidr, strict=False)
                enderecos_existentes = EnderecoIP.objects.filter(bloco=bloco).values_list('ip', flat=True)

                created = 0
                for ip in rede:
                    if str(ip) in enderecos_existentes:
                        continue
                    if ip == rede.network_address or ip == rede.broadcast_address:
                        continue  # pula endereço de rede e broadcast

                    endereco = EnderecoIP(
                        bloco=bloco,
                        ip=str(ip),
                        equipamento=equipamento,
                        porta=porta,
                        finalidade=finalidade,
                        next_hop=next_hop,
                        is_gateway=is_gateway
                    )
                    try:
                        endereco.full_clean()  # Valida antes de salvar
                        endereco.save()
                        created += 1
                    except ValidationError as e:
                        # Pula IP inválido (não quebra o processo)
                        continue

                self.message_user(request, f'{created} endereços IP foram cadastrados com sucesso.',
                                  level=messages.SUCCESS)
                return redirect('admin:appisp_blocoip_changelist')

        else:
            form = EnderecoForm(request=request, user=request.user)

        context = dict(
            self.admin_site.each_context(request),
            form=form,
            bloco=bloco,
        )
        return TemplateResponse(request, "admin/cadastrar_enderecos.html", context)

    def subdividir_view(self, request, bloco_id):
        bloco = get_object_or_404(BlocoIP, id=bloco_id)

        try:
            rede = ip_network(bloco.bloco_cidr, strict=False)
            prefixo_atual = rede.prefixlen

            if (rede.version == 4 and prefixo_atual >= 32) or (rede.version == 6 and prefixo_atual >= 128):
                self.message_user(request, f"O bloco {bloco.bloco_cidr} não pode ser subdividido.",
                                  level=messages.WARNING)
                return redirect('admin:appisp_blocoip_changelist')

            if bloco.sub_blocos.exists():
                self.message_user(request, f"O bloco {bloco.bloco_cidr} já foi subdividido.", level=messages.WARNING)
                return redirect('admin:appisp_blocoip_changelist')

            novo_prefixo = prefixo_atual + 1
            subnets = list(rede.subnets(new_prefix=novo_prefixo))

            for subrede in subnets:
                BlocoIP.objects.create(
                    empresa=bloco.empresa,
                    bloco_cidr=str(subrede),
                    parent=bloco,
                    tipo_ip=bloco.tipo_ip
                )

            self.message_user(request,
                              f"O bloco {bloco.bloco_cidr} foi subdividido com sucesso em {len(subnets)} sub-blocos.",
                              level=messages.SUCCESS)

        except Exception as e:
            self.message_user(request, f"Erro ao subdividir: {e}", level=messages.ERROR)

        return redirect('admin:appisp_blocoip_changelist')

    def subdividir_link(self, obj):
        if obj.sub_blocos.exists():
            return format_html('<span style="color: gray;">Já subdividido</span>')

        try:
            rede = ip_network(obj.bloco_cidr, strict=False)
            prefixo_atual = rede.prefixlen
        except Exception:
            return format_html('<span style="color: red;">CIDR inválido</span>')

        if (rede.version == 4 and prefixo_atual >= 32) or (rede.version == 6 and prefixo_atual >= 128):
            return format_html('<span style="color: gray;">Não pode dividir</span>')

        url = reverse('admin:appisp_blocoip_subdividir', args=[obj.id])
        return format_html(
            '<a class="btn btn-outline-primary btn-sm" '
            'style="padding:2px 8px; border-radius:5px; text-decoration:none;" href="{}">Subdividir</a>',
            url
        )

    subdividir_link.short_description = "Dividir"
    subdividir_link.allow_tags = True

    def gateway(self, obj):
        gw = obj.enderecos.filter(is_gateway=True).first()
        return gw.ip if gw else "-"

    gateway.short_description = "Gateway"

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ('empresa', 'equipamento', BlocoCIDRListFilter, 'parent', 'tipo_ip')
        return (EmpresaUsuarioFilter, EquipamentoEmpresaFilter, BlocoCIDRListFilter, 'tipo_ip')

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if not request.user.is_superuser:
            qs = qs.filter(empresa__usuarios=request.user)

        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "empresa":
                kwargs["queryset"] = Empresa.objects.filter(usuarios=request.user)
            elif db_field.name == "equipamento":
                kwargs["queryset"] = Equipamento.objects.filter(empresa__usuarios=request.user)
            elif db_field.name == "parent":
                kwargs["queryset"] = BlocoIP.objects.filter(empresa__usuarios=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def visualizar_ips(self, request, bloco_id):
        bloco = get_object_or_404(BlocoIP, id=bloco_id)
        rede = ip_network(bloco.bloco_cidr, strict=False)
        enderecos_existentes = EnderecoIP.objects.filter(bloco=bloco).values_list('ip', flat=True)
        ip_info = []

        for ip in rede:
            info = {'ip': str(ip)}
            if ip == rede.network_address:
                info['tipo'] = 'IP de rede'
            elif ip == rede.broadcast_address:
                info['tipo'] = 'IP de broadcast'
            elif str(ip) in enderecos_existentes:
                endereco = EnderecoIP.objects.get(bloco=bloco, ip=str(ip))
                info['tipo'] = 'Cadastrado'
                info['equipamento'] = endereco.equipamento.nome
                info['porta'] = endereco.porta
                info['finalidade'] = endereco.finalidade
                info['next_hop'] = endereco.next_hop
                info['is_gateway'] = endereco.is_gateway
            else:
                info['tipo'] = 'Livre'
            ip_info.append(info)

        context = {
            'bloco': bloco,
            'lista_ips': ip_info,
        }
        return render(request, 'admin/visualizar_ips_do_bloco.html', context)

    def visualizar_ips_link(self, obj):
        if obj.sub_blocos.exists():
            return None  # Não mostra nada

        url = reverse('admin:appisp_blocoip_visualizar_ips', args=[obj.id])
        return format_html('<a class="btn btn-outline-secondary btn-sm"'
                           'style="padding:2px 8px; border-radius:5px; text-decoration:none;" href="{}">IPs</a>', url)

    visualizar_ips_link.short_description = "IPs"


@admin.register(EnderecoIP)
class EnderecoIPAdmin(admin.ModelAdmin):
    list_display = ("ip", "equipamento", "porta", "bloco", "is_gateway", "criado_em")
    list_filter = (EnderecoIPEmpresaFilter, EquipamentoEmpresaFilter, BlocoEmpresaFilter, "is_gateway")
    search_fields = ("ip", "equipamento__nome", "porta__nome")

    form = EnderecoIPForm

    change_list_template = "admin/endereco_ip_changelist.html"  # Template personalizado

    def response_add(self, request, obj, post_url_continue=None):
        """Força o redirecionamento para a listagem correta após adicionar um EnderecoIP"""
        return HttpResponseRedirect(reverse("admin:appisp_enderecoip_changelist"))

    def response_change(self, request, obj):
        """Força o redirecionamento correto após edição"""
        return HttpResponseRedirect(reverse("admin:appisp_enderecoip_changelist"))

    def get_queryset(self, request):
        """Restringe os registros de EnderecoIP para a empresa do usuário"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(equipamento__empresa__usuarios=request.user)

    def get_form(self, request, obj=None, **kwargs):
        """Personaliza o formulário para filtrar os campos de BlocoIP e Equipamento de acordo com o usuário logado"""
        form_class = super().get_form(request, obj, **kwargs)

        if not request.user.is_superuser:
            form_class.base_fields["bloco"].queryset = BlocoIP.objects.filter(empresa__usuarios=request.user)
            form_class.base_fields["equipamento"].queryset = Equipamento.objects.filter(empresa__usuarios=request.user)
            form_class.base_fields["porta"].queryset = Porta.objects.filter(empresa__usuarios=request.user)

        return form_class

    actions = ["sugerir_proximo_ip", "sugerir_proximo_ip_lote"]

    def sugerir_ips_lote(self, request):
        """Tela personalizada para sugerir IPs em lote"""
        if request.method == "POST":
            quantidade = request.POST.get("quantidade")
            if quantidade:
                self.message_user(request, f"IPs sugeridos com sucesso para {quantidade} registros.")
                return HttpResponseRedirect("../")
            else:
                self.message_user(request, "Digite uma quantidade válida.", level=messages.ERROR)

        return render(request, "admin/sugerir_ips_lote.html")

    def adicionar_endereco_ip(self, request):
        """Tela personalizada para adicionar IPs"""
        if request.method == "POST":
            form = EnderecoIPForm(request.POST)

            if form.is_valid():
                empresa = form.cleaned_data["empresa"]
                bloco = form.cleaned_data["bloco"]
                quantidade = form.cleaned_data["quantidade"]

                ips_criados = []
                for i in range(quantidade):
                    endereco = f"{bloco}.{i}"  # Exemplo de lógica para IPs sequenciais
                    ip = EnderecoIP(ip=endereco, bloco=bloco, equipamento=None)
                    ip.save()  # Salva o IP gerado
                    ips_criados.append(endereco)

                self.message_user(
                    request,
                    f"Endereços IP criados com sucesso: {', '.join(ips_criados)}",
                    messages.SUCCESS,
                )
                return HttpResponseRedirect("../")

        else:
            form = EnderecoIPForm()

        context = {"form": form, "opts": self.model._meta}
        return render(request, "admin/adicionar_endereco_ip.html", context)


@admin.register(Porta)
class PortaAdmin(admin.ModelAdmin):
    form = PortaForm
    list_display = ('nome', 'equipamento', 'conexao', 'speed', 'tipo')
    search_fields = ('nome', 'equipamento__nome', 'conexao__nome')
    list_filter = (EmpresaUsuarioFilter, EquipamentoEmpresaFilter, 'speed', 'tipo', )

    change_list_template = "admin/porta_changelist.html"  # Personalizamos o template

    # Incluímos o URL da ação personalizada
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [

            path("adicionar-lote/", self.admin_site.admin_view(self.adicionar_lote), name="adicionar_lote"),
        ]
        return custom_urls + urls

    # Lógica para criar portas em lote
    from django.shortcuts import render, get_object_or_404
    from django.http import HttpResponseRedirect
    from django.contrib import messages
    from .forms import LoteForm  # Importando o formulário

    def adicionar_lote(self, request):
        if request.method == "POST":
            form = LoteForm(request.POST, request=request)  # 🔥 Passamos a request para o form

            if form.is_valid():
                empresa = form.cleaned_data["empresa"]
                equipamento = form.cleaned_data["equipamento"]
                nome_base = form.cleaned_data["nome_base"]
                inicio = form.cleaned_data["inicio"]
                quantidade = form.cleaned_data["quantidade"]
                tipo = form.cleaned_data["tipo"]
                speed = form.cleaned_data["speed"]

                portas_criadas = []
                for i in range(inicio, inicio + quantidade):
                    porta_nome = f"{nome_base}{i}"
                    porta = Porta(
                        nome=porta_nome,
                        equipamento=equipamento,
                        empresa=empresa,
                        tipo=tipo,
                        speed=speed
                    )
                    porta.save()
                    portas_criadas.append(porta_nome)

                self.message_user(
                    request,
                    f"Portas criadas com sucesso: {', '.join(portas_criadas)}",
                    messages.SUCCESS
                )
                return HttpResponseRedirect("../")
            else:
                print("❌ Erros no formulário:", form.errors)

        else:
            form = LoteForm(request=request)  # 🔥 Passamos a request para o form

        context = {
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "admin/adicionar_lote.html", context)

    def get_queryset(self, request):
        """Filtra as portas pela empresa do usuário logado."""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Superusuários veem tudo

        # Filtra as portas apenas das empresas associadas ao usuário
        return qs.filter(empresa__usuarios=request.user)

    def get_fields(self, request, obj=None):
        """Reordena os campos para exibir 'empresa' primeiro."""
        fields = super().get_fields(request, obj)

        if 'equipamento_conexao' in fields and 'conexao' in fields:
            # Move 'equipamento_conexao' para antes de 'conexao'
            fields.remove('equipamento_conexao')
            conexao_index = fields.index('conexao')
            fields.insert(conexao_index, 'equipamento_conexao')  # Inserir 'equipamento_conexao' antes de 'conexao'

        if 'empresa' in fields:
            fields.remove('empresa')
            fields.insert(0, 'empresa')  # Coloca 'empresa' como o primeiro campo
        return fields

    def get_form(self, request, obj=None, **kwargs):
        # Obtém o formulário base
        form = super().get_form(request, obj, **kwargs)

        # Sobrescreve o métod o __init__ do formulário para injetar o request
        class CustomPortaForm(form):
            def __init__(self, *args, **kwargs):
                kwargs['request'] = request
                super().__init__(*args, **kwargs)

        return CustomPortaForm

    def get_search_results(self, request, queryset, search_term):
        """Sobrescreve para incluir o campo de 'equipamento_conexao' na busca."""
        if search_term:
            queryset = queryset.filter(
                Q(nome__icontains=search_term) |
                Q(equipamento__nome__icontains=search_term) |
                Q(conexao__nome__icontains=search_term) |
                Q(equipamento_conexao__nome__icontains=search_term)  # Filtro pelo novo campo
            )
        return queryset, False

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cidade', 'telefone', 'representante', 'status')
    list_filter = ('status', 'representante', 'estado')
    search_fields = ('nome', 'cidade', 'estado', 'cpf_cnpj', 'representante')


@admin.register(Pop)
class PopAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cidade', 'empresa')
    search_fields = ('nome', 'cidade', 'empresa__nome')

    def get_list_filter(self, request):
        """ Aplica o filtro de empresa. """
        if request.user.is_superuser:
            return ('cidade', 'empresa')

        return ('cidade', EmpresaUsuarioFilter)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(empresa__usuarios=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Filtra o campo empresa para mostrar apenas as empresas do usuário logado """
        if db_field.name == "empresa" and not request.user.is_superuser:
            kwargs["queryset"] = Empresa.objects.filter(usuarios=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Fabricante)
class FabricanteAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


# Adicionando uma TAB no modelo para adicionar as Interfaces no modelo
class InterfaceInline(admin.TabularInline):
    model = Interface
    extra = 0  # número de formulários vazios para adicionar
    fields = ('nome', 'tipo', 'poe', 'mgmt_only', 'descricao')
    show_change_link = True

# Model para modelo de equipamentos
@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ('modelo', 'fabricante')
    search_fields = ('modelo',)
    list_filter = ('fabricante',)
    inlines = [InterfaceInline]
    form = ModeloForm


# TAB para portas dentro do equipmaneto
class PortaInline(admin.TabularInline):
    model = Porta
    fields = ('nome', 'tipo', 'speed', 'conexao')  # campos a exibir
    readonly_fields = ('nome', 'tipo', 'speed', 'conexao')
    can_delete = False
    extra = 0
    show_change_link = False

    def has_add_permission(self, request, obj):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    form = EquipamentoForm
    list_display = ('nome', 'ip', 'status', 'pop', 'empresa', 'fabricante', 'tipo')
    search_fields = ('nome', 'ip', 'pop__nome', 'empresa__nome', 'fabricante__nome', 'modelo__modelo', 'tipo')
    inlines = [PortaInline]

    change_list_template = "admin/mapa_rede_changelist.html"  # Personalizamos o template

    def get_form(self, request, obj=None, **kwargs):
        Form = super().get_form(request, obj, **kwargs)

        class FormWithRequest(Form):
            def __init__(self2, *args, **kwargs2):
                kwargs2['request'] = request
                super().__init__(*args, **kwargs2)

        return FormWithRequest

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['user_is_senha'] = request.user.groups.filter(name='Senha').exists()
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def get_list_filter(self, request):
        """ Aplica os filtros personalizados de empresa e POP. """
        if request.user.is_superuser:
            return ('protocolo', 'pop', 'empresa', 'fabricante', 'modelo', 'tipo')

        return ('protocolo', EmpresaUsuarioFilter, PopUsuarioFilter, 'fabricante', 'modelo', 'tipo')

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(empresa__usuarios=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Filtra os campos empresa e pop para mostrar apenas os do usuário """
        if not request.user.is_superuser:
            if db_field.name == "empresa":
                kwargs["queryset"] = Empresa.objects.filter(usuarios=request.user)
            elif db_field.name == "pop":
                kwargs["queryset"] = Pop.objects.filter(empresa__usuarios=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def add_view(self, request, form_url='', extra_context=None):
        if '_popup' in request.GET:
            self.change_form_template = 'admin/popup_add_form.html'  # crie esse arquivo
        return super().add_view(request, form_url, extra_context)

    change_form_template = "admin/equipamento_change_form.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:equipamento_id>/cadastrar-portas/',
                self.admin_site.admin_view(self.cadastrar_portas_view),
                name='cadastrar-portas',
            ),
        ]
        return custom_urls + urls

    def cadastrar_portas_view(self, request, equipamento_id):
        equipamento = get_object_or_404(Equipamento, pk=equipamento_id)
        modelo = equipamento.modelo

        if not modelo:
            messages.error(request, "Este equipamento não tem modelo definido.")
            return redirect("admin:appisp_equipamento_change", equipamento_id)

        interfaces = modelo.interfaces.all()

        # Mapeamentos entre tipo da Interface e tipo/speed da Porta
        tipo_map = {
            '1000base-t': ('Eletrico', '1G'),
            '100base-tx': ('Eletrico', '100M'),
            '10gbase-t': ('Eletrico', '10G'),
            '10gbase-x-sfpp': ('Fibra', '10G'),
            '25gbase-x-sfp28': ('Fibra', '25G'),
            '40gbase-x-qsfpp': ('Fibra', '40G'),
            '100gbase-x-qsfp28': ('Fibra', '100G'),
            'ieee802.11ac': ('Radio', '1G'),
            'ieee802.11n': ('Radio', '100M'),
            'virtual': ('Transporte', '1G'),
            'lag': ('Transporte', '1G'),
        }

        criadas = 0
        for interface in interfaces:
            if not Porta.objects.filter(equipamento=equipamento, nome=interface.nome).exists():
                tipo_interface = interface.tipo.lower() if interface.tipo else ''
                tipo_porta, speed_porta = tipo_map.get(tipo_interface, ('Fibra', '1G'))  # padrão

                Porta.objects.create(
                    equipamento=equipamento,
                    empresa=equipamento.empresa,
                    nome=interface.nome,
                    tipo=tipo_porta,
                    speed=speed_porta,
                    observacao=interface.descricao or ""
                )
                criadas += 1

        if criadas:
            messages.success(request, f"{criadas} portas criadas com sucesso!")
        else:
            messages.info(request, "Nenhuma porta foi criada. Todas já existem.")

        return redirect("admin:appisp_equipamento_change", equipamento_id)


@admin.register(EmpresaToken)
class EmpresaTokenAdmin(admin.ModelAdmin):
    list_display = ("empresa", "token")
    readonly_fields = ("token",)  # Deixa o token apenas para leitura


@admin.register(IntegracaoZabbix)
class IntegracaoZabbixAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'url', 'ativo', 'ultima_sincronizacao', 'testar_conexao_button', 'sincronizar_equipamentos_button', 'sincronizar_portas_link')
    readonly_fields = ('ultima_sincronizacao', 'testar_conexao_button', 'sincronizar_equipamentos_button', 'sincronizar_portas_link')
    fields = (
        'empresa', 'url', 'usuario', 'senha', 'token',
        'observacoes', 'ativo', 'ultima_sincronizacao',
        'testar_conexao_button', 'sincronizar_equipamentos_button', 'sincronizar_portas_link'
    )

    def get_form(self, request, obj=None, **kwargs):
        # Pegando as empresas associadas ao usuário logado
        user_empresas = request.user.empresas.all()  # Acessando o relacionamento reverso do modelo User

        # Criando o formulário customizado
        class IntegracaoZabbixForm(forms.ModelForm):
            empresa = forms.ModelChoiceField(queryset=user_empresas)

            class Meta:
                model = IntegracaoZabbix
                fields = '__all__'

        return IntegracaoZabbixForm

    def get_queryset(self, request):
        # Filtra as integrações para mostrar apenas as da empresa do usuário
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs  # Superusuários podem ver tudo
        return qs.filter(empresa__in=request.user.empresas.all())  # Filtra por empresas associadas ao usuário

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('testar-conexao/<int:pk>/', self.admin_site.admin_view(self.testar_conexao), name='testar_conexao'),
            path('sincronizar-equipamentos/<int:pk>/', self.admin_site.admin_view(self.sincronizar_equipamentos), name='sincronizar_equipamentos'),
            path('<int:pk>/sincronizar_portas/', self.admin_site.admin_view(self.sincronizar_portas), name='sincronizar_portas'),
        ]
        return custom_urls + urls

    def testar_conexao_button(self, obj):
        if obj.pk:
            return format_html(
                '<a class="button" href="{}">🔄 Testar Conexão</a>',
                reverse('admin:testar_conexao', args=[obj.pk])
            )
        return "Salve antes de testar"
    testar_conexao_button.short_description = "Testar Conexão com Zabbix"

    def sincronizar_equipamentos_button(self, obj):
        if obj.pk:
            return format_html(
                '<a class="button" href="{}">🔄 Buscar Equipamentos</a>',
                reverse('admin:sincronizar_equipamentos', args=[obj.pk])
            )
        return "Salve antes de sincronizar"
    sincronizar_equipamentos_button.short_description = "Buscar Equipamentos do Zabbix"

    def sincronizar_portas_link(self, obj):
        if obj.pk:
            url = reverse('admin:sincronizar_portas', args=[obj.pk])
            return format_html('<a class="button" href="{}">🔌 Sincronizar Portas</a>', url)
        return "Salve antes de sincronizar"
    sincronizar_portas_link.short_description = 'Sincronizar Portas'

    def autenticar(self, integracao):
        if integracao.token:
            return integracao.token  # Usar o token se disponível
        # Caso contrário, autenticar com usuário e senha
        payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "user": integracao.usuario,
                "password": integracao.senha
            },
            "id": 1
        }
        response = requests.post(integracao.url, json=payload, timeout=5)
        data = response.json()
        return data.get("result")

    def atualizar_ultima_sincronizacao(self, integracao):
        integracao.ultima_sincronizacao = timezone.now()
        integracao.save()

    def testar_conexao(self, request, pk):
        integracao = get_object_or_404(IntegracaoZabbix, pk=pk)
        try:
            token = self.autenticar(integracao)
            if token:
                self.message_user(request, "✅ Conexão com Zabbix bem-sucedida!")
            else:
                self.message_user(request, "❌ Falha na autenticação com o Zabbix", level='error')
        except Exception as e:
            self.message_user(request, f"⚠️ Erro ao conectar: {str(e)}", level='error')

        return redirect(f'/admin/appisp/integracaozabbix/{pk}/change')

    def sincronizar_equipamentos(self, request, pk):
        integracao = get_object_or_404(IntegracaoZabbix, pk=pk)

        def filtro_equipamento_por_palavras_chave(nome_equipamento, palavras=["sw_", "PPPoE", "BRAS", "BORDA", "CORE", \
                                                                              "OLT", "ROTEADOR", "BGP"]):
            if not palavras:
                return True
            return any(palavra.lower() in nome_equipamento.lower() for palavra in palavras)

        try:
            token = self.autenticar(integracao)

            if not token:
                self.message_user(request, "❌ Erro ao autenticar: Falha na autenticação", level='error')
                return redirect(f'/admin/appisp/integracaozabbix/{pk}/change')

            host_payload = {
                "jsonrpc": "2.0",
                "method": "host.get",
                "params": {
                    "output": ["host", "name"],
                    "selectInterfaces": ["ip"]
                },
                "auth": token,
                "id": 2
            }

            host_response = requests.post(integracao.url, json=host_payload, timeout=10)
            hosts = host_response.json().get("result", [])

            criados = 0
            for host in hosts:
                ip = host.get("interfaces", [{}])[0].get("ip", "")
                nome = host.get("name", "Sem Nome")

                if filtro_equipamento_por_palavras_chave(nome):
                    if not Equipamento.objects.filter(ip=ip, empresa=integracao.empresa).exists():
                        # Certifique-se de que Pop, Fabricante e Modelo existam ou defina uma lógica para obtê-los
                        pop = Pop.objects.filter(empresa=integracao.empresa).first()
                        fabricante = Fabricante.objects.first()
                        modelo = Modelo.objects.first()

                        if pop and fabricante and modelo:
                            Equipamento.objects.create(
                                nome=nome,
                                ip=ip,
                                usuario='admin',
                                senha='admin',
                                porta=22,
                                protocolo='SSH',
                                empresa=integracao.empresa,
                                pop=pop,
                                fabricante=fabricante,
                                modelo=modelo,
                                tipo='Switch',
                                status='Ativo',
                                observacao='Importado do Zabbix'
                            )
                            criados += 1
                        else:
                            print(f"⚠️ Não foi possível criar o equipamento '{nome}' pois Pop, Fabricante ou Modelo não foram encontrados.")
                else:
                    print(f"⏭️ Equipamento ignorado por filtro: {nome}")

            self.message_user(request, f"✅ {criados} equipamento(s) importado(s) com sucesso!")

            # Atualiza a data da última sincronização
            self.atualizar_ultima_sincronizacao(integracao)
        except Exception as e:
            self.message_user(request, f"⚠️ Erro ao sincronizar: {str(e)}", level='error')

        return redirect(f'/admin/appisp/integracaozabbix/{pk}/change')

    def sincronizar_portas(self, request, pk):
        integracao = get_object_or_404(IntegracaoZabbix, pk=pk)

        def filtro_por_palavras_chave(descricao, palavras=["ethernet", "sfp", "eoip", "interface"]):
            if not palavras:
                return True
            return any(palavra.lower() in descricao.lower() for palavra in palavras)

        portas_criadas = 0
        hosts_processados = 0

        try:
            token = self.autenticar(integracao)

            if not token:
                raise Exception("Falha na autenticação")

            hosts_response = requests.post(integracao.url, json={
                "jsonrpc": "2.0",
                "method": "host.get",
                "params": {"output": ["host", "name"]},
                "auth": token,
                "id": 2
            }, timeout=10)
            hosts_response.raise_for_status()
            hosts = hosts_response.json().get("result", [])

            for host in hosts:
                try:
                    hosts_processados += 1
                    nome_host = host["host"]
                    equipamento = Equipamento.objects.filter(nome=nome_host, empresa=integracao.empresa).first()

                    if not equipamento:
                        continue

                    item_payload = {
                        "jsonrpc": "2.0",
                        "method": "item.get",
                        "params": {
                            "output": ["name", "key_"],
                            "hostids": host["hostid"]
                        },
                        "auth": token,
                        "id": 3
                    }

                    item_response = requests.post(integracao.url, json=item_payload, timeout=10)
                    item_response.raise_for_status()
                    items = item_response.json().get("result", [])

                    nomes_interface = {}
                    itens_porta = []

                    nomes_interfaces_list = []

                    for item in items:
                        chave = item.get("key_", "")
                        nome = item.get("name", "").strip()

                        if chave.startswith("net.if.type"):
                            nome_interface = None
                            nome_interface_match = re.search(r'Interface (.+?)(?:\(|:)', nome)
                            if nome_interface_match:
                                nome_interface = nome_interface_match.group(1).strip()
                                nome_interface = re.sub(r'\([^)]+\)', '', nome_interface).strip()
                            else:
                                nome_interface_match_alt = re.search(r'(\S+)\s*Interface', nome)
                                if nome_interface_match_alt:
                                    nome_interface = nome_interface_match_alt.group(1).strip()
                                    nome_interface = re.sub(r'\([^)]+\)', '', nome_interface).strip()
                                else:
                                    nome_interface = nome
                                    nome_interface = re.sub(r'\([^)]+\)', '', nome_interface).strip()

                            if nome_interface:
                                nomes_interfaces_list.append(nome_interface)

                        elif chave.startswith(("net.if.in", "net.if.out", "net.if.speed")):
                            itens_porta.append(item)

                    nomes_processados = set()
                    interface_index = 0

                    for item in itens_porta:
                        chave = item.get("key_", "")
                        nome_item = item.get("name", "").strip()
                        nome_porta = None

                        if interface_index < len(nomes_interfaces_list):
                            nome_porta = nomes_interfaces_list[interface_index]
                            interface_index += 1
                        else:
                            nome_porta_match = re.search(r'Interface (.+?)(?:\(|:)', nome_item)
                            if nome_porta_match:
                                nome_porta = nome_porta_match.group(1).strip()
                                nome_porta = re.sub(r'\([^)]+\)', '', nome_porta).strip()
                            else:
                                nome_porta_match_alt = re.search(r'(\S+)\s*Interface', nome_item)
                                if nome_porta_match_alt:
                                    nome_porta = nome_porta_match_alt.group(1).strip()
                                    nome_porta = re.sub(r'\([^)]+\)', '', nome_porta).strip()
                                else:
                                    continue

                        if nome_porta:
                            nome_porta_completo = nome_porta.strip()
                            if "(" not in nome_porta_completo:
                                nome_porta_completo = nome_porta_completo

                            if not filtro_por_palavras_chave(nome_porta_completo):
                                continue

                            nome_normalizado = nome_porta_completo.lower().replace(" ", "").replace("/", "").replace("-", "")
                            if nome_normalizado in nomes_processados:
                                continue
                            nomes_processados.add(nome_normalizado)

                            try:
                                porta, criada = Porta.objects.update_or_create(
                                    equipamento=equipamento,
                                    nome=nome_porta_completo,
                                    defaults={
                                        'empresa': equipamento.empresa,
                                        'speed': '1G',
                                        'tipo': 'Fibra',
                                        'observacao': 'Importado do Zabbix',
                                    }
                                )
                                if criada:
                                    portas_criadas += 1
                            except Exception as db_error:
                                import traceback
                                print(f"⚠️ Erro ao salvar/atualizar porta: {db_error}")
                                traceback.print_exc()

                except requests.exceptions.RequestException as req_err_host:
                    print(f"⚠️ Erro de comunicação com o Zabbix ao processar o host {host['host']}: {req_err_host}")
                except Exception as e_host:
                    import traceback
                    print(f"⚠️ Erro ao processar o host {host['host']}: {e_host}")
                    traceback.print_exc()

            self.message_user(request,
                              f"✅ {portas_criadas} porta(s) importada(s) com sucesso de {hosts_processados} hosts!")

            # Atualiza a data da última sincronização
            self.atualizar_ultima_sincronizacao(integracao)

        except requests.exceptions.RequestException as req_err_global:
            self.message_user(request, f"⚠️ Erro de comunicação global com o Zabbix: {req_err_global}",
                              level=messages.ERROR)
        except Exception as e_global:
            self.message_user(request, f"⚠️ Erro global ao buscar portas: {str(e_global)}", level=messages.ERROR)

        return redirect(f'/admin/appisp/integracaozabbix/{pk}/change')


class IntegracaoNetboxAdmin(admin.ModelAdmin):
    readonly_fields = ('ultima_sincronizacao', 'acoes_netbox')

    fieldsets = (
        (None, {
            'fields': ('empresa', 'url', 'token', 'ativo', 'observacoes', 'ultima_sincronizacao', 'acoes_netbox')
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/testar-token/', self.admin_site.admin_view(self.testar_token), name='testar_token_netbox'),
            path('<int:pk>/obter-equipamentos/', self.admin_site.admin_view(self.obter_equipamentos), name='obter_equipamentos_netbox'),
            path('<int:pk>/obter-blocos-ip/', self.admin_site.admin_view(self.obter_blocos_ip), name='obter_blocos_ip_netbox'),
            path('<int:pk>/obter-enderecos-ip/', self.admin_site.admin_view(self.obter_enderecos_ip), name='obter_enderecos_ip_netbox'),
            path('<int:pk>/sincronizar-equipamentos/', self.admin_site.admin_view(self.sincronizar_equipamentos_netbox), name='sincronizar_equipamentos_netbox'),
            path('<int:pk>/sincronizar-portas/', self.admin_site.admin_view(self.sincronizar_portas_netbox),
                 name='sincronizar_portas_netbox'),
            path('<int:pk>/sincronizar-blocos-ip/', self.admin_site.admin_view(self.sincronizar_blocos_netbox),
                 name='sincronizar_blocos_ip_netbox'),
            path('<int:pk>/sincronizar-enderecos-ip/', self.admin_site.admin_view(self.sincronizar_enderecos_ip_netbox),
                 name='sincronizar_enderecos_ip_netbox'),

        ]
        return custom_urls + urls

    def acoes_netbox(self, obj):
        if not obj.pk:
            return "Salve a integração antes de usar as ações."

        return format_html(
            '<a class="button" href="{}">Testar Token</a>&nbsp;'
            '<a class="button" href="{}">Obter Equipamentos</a>&nbsp;'
            '<a class="button" href="{}">Obter Blocos IP</a>&nbsp;'
            '<a class="button" href="{}">Obter Endereços IP</a>&nbsp;'
            '<a class="button" style="background-color:green;color:white;" href="{}">Sincronizar Equipamentos</a>&nbsp;'
            '<a class="button" style="background-color:#0073e6;color:white;" href="{}">Sincronizar Portas</a>'
            '<a class="button" style="background-color:#5c1fff;color:white;" href="{}">Sincronizar Blocos IP</a>'
            '<a class="button" style="background-color:#5c1fff;color:white;" href="{}">Sincronizar Endereços IP</a>',
            reverse('admin:testar_token_netbox', args=[obj.pk]),
            reverse('admin:obter_equipamentos_netbox', args=[obj.pk]),
            reverse('admin:obter_blocos_ip_netbox', args=[obj.pk]),
            reverse('admin:obter_enderecos_ip_netbox', args=[obj.pk]),
            reverse('admin:sincronizar_equipamentos_netbox', args=[obj.pk]),
            reverse('admin:sincronizar_portas_netbox', args=[obj.pk]),
            reverse('admin:sincronizar_blocos_ip_netbox', args=[obj.pk]),
            reverse('admin:sincronizar_enderecos_ip_netbox', args=[obj.pk]),
        )
    acoes_netbox.short_description = "Ações da Integração"
    acoes_netbox.allow_tags = True

    def testar_token(self, request, pk):
        obj = get_object_or_404(IntegracaoNetbox, pk=pk)
        headers = {"Authorization": f"Token {obj.token}"}
        try:
            resp = requests.get(f"{obj.url}status/", headers=headers, timeout=5)
            if resp.status_code == 200:
                messages.success(request, f"✅ Token válido para {obj.empresa.nome}.")
            else:
                messages.error(request, f"❌ Token inválido. Código: {resp.status_code}")
        except Exception as e:
            messages.error(request, f"❌ Erro ao testar token: {e}")
        return HttpResponseRedirect(f"/admin/appisp/integracaonetbox/{pk}/change/")

    def obter_equipamentos(self, request, pk):
        obj = get_object_or_404(IntegracaoNetbox, pk=pk)
        headers = {"Authorization": f"Token {obj.token}"}
        try:
            url = f"{obj.url}dcim/devices/"
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("count", len(data.get("results", [])))
                messages.success(request, f"📦 {total} equipamentos obtidos com sucesso.")
            else:
                messages.error(request, f"Erro ao obter equipamentos. Código: {resp.status_code}")
        except Exception as e:
            messages.error(request, f"Erro ao obter equipamentos: {e}")
        return HttpResponseRedirect(f"/admin/appisp/integracaonetbox/{pk}/change/")

    def obter_blocos_ip(self, request, pk):
        obj = get_object_or_404(IntegracaoNetbox, pk=pk)
        headers = {"Authorization": f"Token {obj.token}"}
        try:
            url = f"{obj.url}ipam/prefixes/"
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("count", len(data.get("results", [])))
                messages.success(request, f"📚 {total} blocos de IP obtidos com sucesso.")
            else:
                messages.error(request, f"Erro ao obter blocos IP. Código: {resp.status_code}")
        except Exception as e:
            messages.error(request, f"Erro ao obter blocos de IP: {e}")
        return HttpResponseRedirect(f"/admin/appisp/integracaonetbox/{pk}/change/")

    def obter_enderecos_ip(self, request, pk):
        obj = get_object_or_404(IntegracaoNetbox, pk=pk)
        headers = {"Authorization": f"Token {obj.token}"}
        try:
            url = f"{obj.url}ipam/ip-addresses/"
            resp = requests.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                total = data.get("count", len(data.get("results", [])))
                messages.success(request, f"🌐 {total} endereços IP obtidos com sucesso.")
            else:
                messages.error(request, f"Erro ao obter endereços IP. Código: {resp.status_code}")
        except Exception as e:
            messages.error(request, f"Erro ao obter endereços IP: {e}")
        return HttpResponseRedirect(f"/admin/appisp/integracaonetbox/{pk}/change/")

    def sincronizar_equipamentos_netbox(self, request, pk):
        from django.shortcuts import get_object_or_404, redirect
        import requests
        from .models import Equipamento, Fabricante, Modelo, Pop, IntegracaoNetbox  # ajuste o caminho se necessário

        integracao = get_object_or_404(IntegracaoNetbox, pk=pk)
        headers = {"Authorization": f"Token {integracao.token}"}
        criados = 0

        try:
            url = f"{integracao.url.rstrip('/')}/dcim/devices/"  # com /api/ incluso
            while url:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                dados = response.json()
                dispositivos = dados.get('results', [])
                url = dados.get('next')  # próxima página ou None

                for dispositivo in dispositivos:
                    nome = dispositivo.get("name", "Sem Nome")

                    # IP
                    primary_ip = dispositivo.get("primary_ip4")
                    ip = primary_ip.get("address").split('/')[0] if primary_ip and primary_ip.get(
                        "address") else "0.0.0.0"

                    # Modelo e Fabricante
                    device_type = dispositivo.get("device_type") or {}
                    nome_modelo = device_type.get("model", "Desconhecido")
                    fabricante_data = device_type.get("manufacturer") or {}
                    nome_fabricante = fabricante_data.get("name", "Desconhecido")

                    # Verifica se já existe um equipamento com mesmo nome e empresa
                    if not Equipamento.objects.filter(nome=nome, empresa=integracao.empresa).exists():
                        # Buscar ou criar fabricante
                        fabricante, _ = Fabricante.objects.get_or_create(nome=nome_fabricante)

                        # Buscar ou criar modelo
                        modelo, _ = Modelo.objects.get_or_create(modelo=nome_modelo, fabricante=fabricante)

                        # Buscar ou criar POP (usa o primeiro POP da empresa)
                        pop = Pop.objects.filter(empresa=integracao.empresa).first()
                        if not pop:
                            pop = Pop.objects.create(
                                nome="POP Importado",
                                endereco="Desconhecido",
                                cidade="Desconhecida",
                                empresa=integracao.empresa
                            )

                        # Criar o equipamento
                        Equipamento.objects.create(
                            nome=nome,
                            ip=ip,
                            usuario='admin',
                            senha='admin',
                            porta=22,
                            protocolo='SSH',
                            empresa=integracao.empresa,
                            pop=pop,
                            fabricante=fabricante,
                            modelo=modelo,
                            tipo='Switch',
                            status='Ativo',
                            observacao='Importado do NetBox'
                        )
                        criados += 1

            self.message_user(request, f"✅ {criados} equipamento(s) importado(s) com sucesso do NetBox!")
            self.atualizar_ultima_sincronizacao(integracao)

        except Exception as e:
            self.message_user(request, f"⚠️ Erro ao sincronizar do NetBox: {str(e)}", level='error')

        return redirect(f'/admin/appisp/integracaonetbox/{pk}/change')

    def sincronizar_portas_netbox(self, request, pk):
        from .models import Equipamento, Porta
        integracao = get_object_or_404(IntegracaoNetbox, pk=pk)
        headers = {"Authorization": f"Token {integracao.token}"}
        total_criadas = 0
        total_atualizadas = 0

        try:
            url = f"{integracao.url.rstrip('/')}/dcim/interfaces/?limit=100"

            while url:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                interfaces = data.get('results', [])
                url = data.get('next')

                for iface in interfaces:
                    device = iface.get('device')
                    device_name = device.get('name') if device else None
                    port_name = iface.get('name')

                    if not device_name or not port_name:
                        continue

                    equipamento = Equipamento.objects.filter(nome=device_name, empresa=integracao.empresa).first()
                    if not equipamento:
                        continue

                    porta, created = Porta.objects.update_or_create(
                        equipamento=equipamento,
                        nome=port_name,
                        defaults={
                            "tipo": "Fibra",  # ou outra lógica se quiser mapear o tipo real
                            "speed": "1G",  # valor default, pode adaptar se quiser usar info do NetBox
                            "observacao": "",
                            "empresa": equipamento.empresa,
                        }
                    )

                    if created:
                        total_criadas += 1
                    else:
                        total_atualizadas += 1

            self.message_user(request,
                              f"🔌 {total_criadas} portas criadas e {total_atualizadas} atualizadas com sucesso.")
            self.atualizar_ultima_sincronizacao(integracao)

        except Exception as e:
            self.message_user(request, f"⚠️ Erro ao sincronizar portas: {str(e)}", level='error')

        return redirect(f"/admin/appisp/integracaonetbox/{pk}/change")

    def sincronizar_blocos_netbox(self, request, pk):
        from .models import BlocoIP, Equipamento
        integracao = get_object_or_404(IntegracaoNetbox, pk=pk)
        headers = {"Authorization": f"Token {integracao.token}"}
        total_criados = 0
        total_atualizados = 0
        erros = []

        try:
            url = f"{integracao.url.rstrip('/')}/ipam/prefixes/?limit=100"

            while url:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                prefixos = data.get('results', [])
                url = data.get('next')

                for prefixo in prefixos:
                    try:
                        cidr = prefixo.get('prefix')
                        descricao = prefixo.get('description', '')
                        tipo_ip = 'IPv6' if ':' in cidr else 'IPv4'
                        equipamento = None

                        device_info = prefixo.get('device')
                        if device_info and isinstance(device_info, dict):
                            device_name = device_info.get('name')
                            if device_name:
                                equipamento = Equipamento.objects.filter(nome=device_name,
                                                                         empresa=integracao.empresa).first()

                        bloco, created = BlocoIP.objects.update_or_create(
                            empresa=integracao.empresa,
                            bloco_cidr=cidr,
                            defaults={
                                'tipo_ip': tipo_ip,
                                'descricao': descricao,
                                'equipamento': equipamento
                            }
                        )

                        if created:
                            total_criados += 1
                        else:
                            total_atualizados += 1

                    except Exception as e:
                        erros.append(f"{cidr}: {str(e)}")

            self.atualizar_ultima_sincronizacao(integracao)

            mensagem = f"✅ {total_criados} blocos criados, {total_atualizados} atualizados."
            if erros:
                mensagem += f" ⚠️ {len(erros)} erros durante a sincronização. Veja abaixo:\n"
                for erro in erros[:10]:  # Mostra no máximo 10 erros no admin
                    mensagem += f"\n• {erro}"
                if len(erros) > 10:
                    mensagem += f"\n... e mais {len(erros) - 10} erros."

            self.message_user(request, mensagem, level='warning' if erros else 'info')

        except Exception as e:
            self.message_user(request, f"⚠️ Erro geral ao sincronizar blocos de IP: {str(e)}", level='error')

        return redirect(f"/admin/appisp/integracaonetbox/{pk}/change")

    def sincronizar_enderecos_ip_netbox(self, request, pk):
        from .models import EnderecoIP, BlocoIP, Equipamento, Porta
        integracao = get_object_or_404(IntegracaoNetbox, pk=pk)
        headers = {"Authorization": f"Token {integracao.token}"}
        total_criados = 0
        total_atualizados = 0
        erros = []

        try:
            url = f"{integracao.url.rstrip('/')}/ipam/ip-addresses/?limit=100"

            while url:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                data = response.json()
                ip_addresses = data.get('results', [])
                url = data.get('next')

                for ip_info in ip_addresses:
                    try:
                        ip = ip_info.get('address')
                        equipamento_info = ip_info.get('device')
                        porta_info = ip_info.get('interface')
                        bloco_info = ip_info.get('prefix')

                        # Adiciona uma checagem para garantir que todos os dados necessários estão presentes
                        if not ip or not equipamento_info or not porta_info or not bloco_info:
                            erros.append(f"Faltando dados para o IP: {ip_info}")
                            continue

                        # Debug: Imprimir ip_info para investigar se os dados estão completos
                        print(f"Processando IP: {ip_info}")

                        # Encontrar o bloco de IP
                        bloco_cidr = bloco_info.get('prefix')
                        bloco = BlocoIP.objects.filter(bloco_cidr=bloco_cidr, empresa=integracao.empresa).first()
                        if not bloco:
                            erros.append(f"Bloco de IP não encontrado para o CIDR: {bloco_cidr}")
                            continue

                        # Encontrar o equipamento e porta
                        equipamento = Equipamento.objects.filter(nome=equipamento_info.get('name'),
                                                                 empresa=integracao.empresa).first()
                        if not equipamento:
                            erros.append(f"Equipamento não encontrado: {equipamento_info.get('name')}")
                            continue

                        porta = Porta.objects.filter(nome=porta_info.get('name'), equipamento=equipamento).first()
                        if not porta:
                            erros.append(
                                f"Porta não encontrada: {porta_info.get('name')} no equipamento {equipamento.nome}")
                            continue

                        # Criar ou atualizar o endereço IP
                        endereco_ip, created = EnderecoIP.objects.update_or_create(
                            ip=ip,
                            equipamento=equipamento,
                            porta=porta,
                            bloco=bloco,
                            defaults={
                                'finalidade': ip_info.get('description', ''),
                                'next_hop': ip_info.get('gateway', ''),
                                'is_gateway': ip_info.get('is_gateway', False),
                            }
                        )

                        if created:
                            total_criados += 1
                        else:
                            total_atualizados += 1

                    except Exception as e:
                        erros.append(f"Erro ao processar o IP {ip}: {str(e)}")

            self.atualizar_ultima_sincronizacao(integracao)

            mensagem = f"✅ {total_criados} IPs criados, {total_atualizados} atualizados."
            if erros:
                mensagem += f" ⚠️ {len(erros)} erros durante a sincronização. Veja abaixo:\n"
                for erro in erros[:10]:  # Mostra no máximo 10 erros no admin
                    mensagem += f"\n• {erro}"
                if len(erros) > 10:
                    mensagem += f"\n... e mais {len(erros) - 10} erros."

            self.message_user(request, mensagem, level='warning' if erros else 'info')

        except Exception as e:
            self.message_user(request, f"⚠️ Erro geral ao sincronizar endereços de IP: {str(e)}", level='error')

        return redirect(f"/admin/appisp/integracaonetbox/{pk}/change")

    def atualizar_ultima_sincronizacao(self, integracao):
        integracao.ultima_sincronizacao = now()
        integracao.save()


# Classe personalizada de Admin
class CustomAdminSite(AdminSite):
    site_header = "Documentação de Rede"
    site_title = "ISP-DOC"
    index_title = "Bem-vindo ao ISP-DOC"

    # Adicionando as URLs para mapa-rede e mapa-rack
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('mapa-rede/', self.admin_view(mapa), name='mapa-rede'),
            path('mapa-rack/', self.admin_view(mapa_racks), name='mapa-rack'),
        ]
        return custom_urls + urls

    # Adicionando os links ao menu
    def each_context(self, request):
        context = super().each_context(request)
        context['custom_menu_links'] = [
            {
                'name': _('Mapa de Rede'),
                'url': reverse('admin:mapa-rede'),
                'icon': 'fa fa-map',  # Opcional, ícone para o menu
            },
            {
                'name': _('Mapa de Rack'),
                'url': reverse('admin:mapa-rack'),
                'icon': 'fa fa-cogs',  # Opcional, ícone para o menu
            }
        ]
        return context


# Instanciando a classe personalizada do Admin
admin_site = CustomAdminSite(name='custom_admin')

# Registrando os modelos padrão do Django
admin_site.register(User, UserAdmin)
admin_site.register(Group, GroupAdmin)

# Registrando os modelos do Admin
admin_site.register(Equipamento, EquipamentoAdmin)
admin_site.register(Porta, PortaAdmin)
admin_site.register(Empresa, EmpresaAdmin)
admin_site.register(Pop, PopAdmin)
admin_site.register(Fabricante, FabricanteAdmin)
admin_site.register(Modelo, ModeloAdmin)
admin_site.register(BlocoIP, BlocoIPAdmin)
admin_site.register(EnderecoIP, EnderecoIPAdmin)
admin_site.register(Rack, RackAdmin)
admin_site.register(RackEquipamento, RackEquipamentoAdmin)
admin_site.register(MaquinaVirtual, MaquinaVirtualAdmin)
admin_site.register(Vlan, VlanAdmin)
admin_site.register(VlanPorta, VlanPortaAdmin)
admin_site.register(EmpresaToken, EmpresaTokenAdmin)
admin_site.register(IntegracaoZabbix, IntegracaoZabbixAdmin)
admin_site.register(IntegracaoNetbox, IntegracaoNetboxAdmin)

# Em vez de usar admin.site, agora usamos admin_site
# Para fazer isso funcionar, você precisará alterar as URLs do seu projeto Django para usar o custom_admin

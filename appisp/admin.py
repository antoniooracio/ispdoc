import json

import requests
import re
from django.contrib import admin, messages
from django import forms
from django.urls import path
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.admin import AdminSite
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseRedirect
from .forms import PortaForm, RackForm, RackEquipamentoForm, EnderecoIPForm
from .views import mapa, mapa_racks
from django.contrib.admin import SimpleListFilter
from .models import Empresa, Pop, Fabricante, Modelo, Equipamento, Porta, BlocoIP, EnderecoIP, Rack, RackEquipamento, \
    MaquinaVirtual, Disco, Rede, Vlan, VlanPorta, EmpresaToken, IntegracaoZabbix
import ipaddress
from django.utils.html import format_html



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
    list_display = ('nome', 'empresa', 'equipamento', 'sistema_operacional', 'tipo_acesso')
    search_fields = ('nome', 'empresa__nome', 'equipamento__nome', 'sistema_operacional')
    list_filter = ('empresa', 'equipamento')
    inlines = [DiscoInline, RedeInline]  # Adiciona os campos de discos e redes no formulário

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


@admin.register(Rack)
class RackAdmin(admin.ModelAdmin):
    form = RackForm  # Usa o formulário com validação
    list_display = ('nome', 'pop', 'empresa', 'us', 'modelo')
    list_filter = ('empresa', 'pop')
    search_fields = ('nome', 'pop__nome', 'empresa__nome')
    ordering = ('empresa', 'pop', 'nome')

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


@admin.register(BlocoIP)
class BlocoIPAdmin(admin.ModelAdmin):
    list_display = (
    'empresa', 'equipamento', 'bloco_cidr', 'tipo_ip', 'next_hop', 'descricao', 'gateway', 'parent', 'criado_em')
    search_fields = ('bloco_cidr', 'empresa__nome', 'equipamento__nome')
    list_filter = ('tipo_ip', 'empresa', 'equipamento', 'parent')
    form = BlocoIPForm

    def gateway(self, obj):
        """Mostra o IP configurado como Gateway"""
        gw = obj.enderecos.filter(is_gateway=True).first()
        return gw.ip if gw else "Nenhum"

    gateway.short_description = "Gateway"

    def get_list_filter(self, request):
        if request.user.is_superuser:
            return ('empresa', 'equipamento', 'bloco_cidr', 'parent', 'tipo_ip')
        return (EmpresaUsuarioFilter, EquipamentoEmpresaFilter, 'bloco_cidr', 'tipo_ip')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(empresa__usuarios=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            if db_field.name == "empresa":
                kwargs["queryset"] = Empresa.objects.filter(usuarios=request.user)
            elif db_field.name == "equipamento":
                kwargs["queryset"] = Equipamento.objects.filter(empresa__usuarios=request.user)
            elif db_field.name == "parent":
                kwargs["queryset"] = BlocoIP.objects.filter(empresa__usuarios=request.user)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(EnderecoIP)
class EnderecoIPAdmin(admin.ModelAdmin):
    list_display = ("ip", "equipamento", "porta", "bloco", "is_gateway", "criado_em")
    list_filter = (EnderecoIPEmpresaFilter, EquipamentoEmpresaFilter, BlocoEmpresaFilter, "is_gateway")
    search_fields = ("ip", "equipamento__nome", "porta__nome")

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
        """
        Personaliza o formulário para filtrar os campos de BlocoIP e Equipamento de acordo com o usuário logado
        """
        form_class = super().get_form(request, obj, **kwargs)

        # Filtro para o campo 'bloco' baseado no usuário logado
        if not request.user.is_superuser:
            form_class.base_fields["bloco"].queryset = BlocoIP.objects.filter(empresa__usuarios=request.user)

        # Filtro para o campo 'equipamento' baseado no usuário logado
        if not request.user.is_superuser:
            form_class.base_fields["equipamento"].queryset = Equipamento.objects.filter(empresa__usuarios=request.user)

            # Filtro para o campo 'equipamento' baseado no usuário logado
            if not request.user.is_superuser:
                form_class.base_fields["porta"].queryset = Porta.objects.filter(
                    empresa__usuarios=request.user)

        return form_class

    actions = ["sugerir_proximo_ip"]

    def sugerir_proximo_ip(self, request, queryset):
        """Sugere e preenche o próximo IP disponível para cada registro"""
        for endereco in queryset:
            if not endereco.ip:
                endereco.ip = endereco.bloco.sugerir_proximo_ip()
                endereco.save()

        self.message_user(request, "IP sugerido e salvo automaticamente.")

    sugerir_proximo_ip.short_description = "Sugerir próximo IP disponível"

    # Adicionamos a URL personalizada para o botão de adicionar IPs em lote
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("adicionar-endereco-ip/", self.admin_site.admin_view(self.adicionar_endereco_ip),
                 name="adicionar_endereco_ip"),
        ]
        return custom_urls + urls

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
                    ip.save()
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


@admin.register(Modelo)
class ModeloAdmin(admin.ModelAdmin):
    list_display = ('modelo', 'fabricante')
    search_fields = ('modelo',)
    list_filter = ('fabricante',)


@admin.register(Equipamento)
class EquipamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ip', 'status', 'pop', 'empresa', 'fabricante', 'tipo')
    search_fields = ('nome', 'ip', 'pop__nome', 'empresa__nome', 'fabricante__nome', 'modelo__modelo', 'tipo')

    change_list_template = "admin/mapa_rede_changelist.html"  # Personalizamos o template

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


@admin.register(EmpresaToken)
class EmpresaTokenAdmin(admin.ModelAdmin):
    list_display = ("empresa", "token")
    readonly_fields = ("token",)  # Deixa o token apenas para leitura


@admin.register(IntegracaoZabbix)
class IntegracaoZabbixAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'url', 'ativo', 'ultima_sincronizacao', 'testar_conexao_button', 'sincronizar_equipamentos_button', 'sincronizar_portas_link')
    readonly_fields = ('ultima_sincronizacao', 'testar_conexao_button', 'sincronizar_equipamentos_button', 'sincronizar_portas_link')
    fields = (
        'empresa', 'url', 'usuario', 'senha',
        'observacoes', 'ativo', 'ultima_sincronizacao',
        'testar_conexao_button', 'sincronizar_equipamentos_button', 'sincronizar_portas_link'
    )

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

    def testar_conexao(self, request, pk):
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
                self.message_user(request, "✅ Conexão com Zabbix bem-sucedida!")
            else:
                self.message_user(request, f"❌ Falha na autenticação com o Zabbix: {data.get('error')}", level='error')
        except Exception as e:
            self.message_user(request, f"⚠️ Erro ao conectar: {str(e)}", level='error')

        return redirect(f'/admin/appisp/integracaozabbix/{pk}/change')

    def sincronizar_equipamentos(self, request, pk):
        integracao = get_object_or_404(IntegracaoZabbix, pk=pk)

        auth_payload = {
            "jsonrpc": "2.0",
            "method": "user.login",
            "params": {
                "user": integracao.usuario,
                "password": integracao.senha
            },
            "id": 1
        }

        try:
            login_response = requests.post(integracao.url, json=auth_payload, timeout=5)
            login_data = login_response.json()
            token = login_data.get("result")

            if not token:
                self.message_user(request, f"❌ Erro ao autenticar: {login_data.get('error')}", level='error')
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

                if not Equipamento.objects.filter(ip=ip).exists():
                    Equipamento.objects.create(
                        nome=nome,
                        ip=ip,
                        usuario='admin',
                        senha='admin',
                        porta=22,
                        protocolo='SSH',
                        empresa=integracao.empresa,
                        pop=Pop.objects.filter(empresa=integracao.empresa).first(),
                        fabricante=Fabricante.objects.first(),
                        modelo=Modelo.objects.first(),
                        tipo='Switch',
                        status='Ativo',
                        observacao='Importado do Zabbix'
                    )
                    criados += 1

            self.message_user(request, f"✅ {criados} equipamento(s) importado(s) com sucesso!")
        except Exception as e:
            self.message_user(request, f"⚠️ Erro ao sincronizar: {str(e)}", level='error')

        return redirect(f'/admin/appisp/integracaozabbix/{pk}/change')

    def sincronizar_portas(self, request, pk):
        integracao = get_object_or_404(IntegracaoZabbix, pk=pk)

        def filtro_por_palavras_chave(descricao, palavras=["ethernet"]):
            if not palavras:
                return True
            return any(palavra.lower() in descricao.lower() for palavra in palavras)

        try:
            login_response = requests.post(integracao.url, json={
                "jsonrpc": "2.0",
                "method": "user.login",
                "params": {"user": integracao.usuario, "password": integracao.senha},
                "id": 1
            }, timeout=10)
            login_response.raise_for_status()  # Levanta uma exceção para erros HTTP
            token = login_response.json().get("result")
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

            portas_criadas = 0

            for host in hosts:
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

                for item in items:
                    chave = item.get("key_", "")
                    nome = item.get("name", "").strip()

                    if chave.startswith("net.if.type"):
                        match = re.search(r'net\.if\.type\[(.*?)\]', chave)
                        if match:
                            indice = match.group(1).replace("ifType.", "")
                            nome_interface_match = re.search(r'Interface (.+?)(?:\(|:)', nome)
                            if nome_interface_match:
                                nome_interface = nome_interface_match.group(1).strip()
                                nomes_interface[indice] = nome_interface
                            else:
                                nome_interface_match_alt = re.search(r'(\w+)\s*Interface', nome)
                                if nome_interface_match_alt:
                                    nome_interface = nome_interface_match_alt.group(1).strip()
                                    nomes_interface[indice] = nome_interface
                                else:
                                    nome_interface = nome  # Se não encontrar "Interface", usa o nome completo
                                print(
                                    f"⚠️ Atenção: Padrão de nome de interface não reconhecido para '{nome}'. Usando '{nome_interface}'.")

                    elif chave.startswith(("net.if.in", "net.if.out", "net.if.speed")):
                        itens_porta.append(item)

                nomes_processados = set()

                for item in itens_porta:
                    chave = item.get("key_", "")
                    match = re.search(r'net\.if\.\w+\[(.*?)\]', chave)
                    if not match:
                        continue

                    indice = match.group(1)
                    nome_porta = nomes_interface.get(indice)
                    if not nome_porta:
                        continue

                    if not filtro_por_palavras_chave(nome_porta, palavras=[]):
                        continue

                    nome_normalizado = nome_porta.lower().replace(" ", "").replace("/", "").replace("-", "")
                    if nome_normalizado in nomes_processados:
                        continue
                    nomes_processados.add(nome_normalizado)

                    try:
                        porta, criada = Porta.objects.update_or_create(
                            equipamento=equipamento,
                            nome=nome_porta,
                            defaults={
                                'empresa': equipamento.empresa,
                                'speed': '1 Gbps',
                                'tipo': 'Fibra',
                                'observacao': 'Importado do Zabbix',
                            }
                        )

                        # Atualiza empresa caso não exista
                        if not criada and not porta.empresa:
                            porta.empresa = equipamento.empresa
                            porta.save(update_fields=['empresa'])

                        if criada:
                            portas_criadas += 1
                    except Exception as db_error:
                        print(
                            f"⚠️ Erro ao salvar/atualizar porta '{nome_porta}' para o equipamento '{equipamento.nome}': {db_error}")

            self.message_user(request, f"✅ {portas_criadas} porta(s) importada(s) com sucesso!")

        except requests.exceptions.RequestException as req_err:
            self.message_user(request, f"⚠️ Erro de comunicação com o Zabbix: {req_err}", level=messages.ERROR)
        except Exception as e:
            self.message_user(request, f"⚠️ Erro ao buscar portas: {str(e)}", level=messages.ERROR)

        return redirect(f'/admin/appisp/integracaozabbix/{pk}/change')


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

# Em vez de usar admin.site, agora usamos admin_site
# Para fazer isso funcionar, você precisará alterar as URLs do seu projeto Django para usar o custom_admin

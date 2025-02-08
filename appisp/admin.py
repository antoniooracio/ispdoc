from django.contrib import admin, messages
from django import forms
from django.urls import path
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.admin import AdminSite
from django.shortcuts import render
from django.http import HttpResponseRedirect
from .forms import PortaForm, RackForm, RackEquipamentoForm
from .views import mapa, mapa_racks
from django.contrib.admin import SimpleListFilter
from .models import Empresa, Pop, Fabricante, Modelo, Equipamento, Porta, BlocoIP, EnderecoIP, Rack, RackEquipamento, MaquinaVirtual, Disco, Rede
import json

class DiscoInline(admin.TabularInline):  # Ou admin.StackedInline para exibição vertical
    model = Disco
    extra = 1  # Número inicial de campos exibidos


class RedeInline(admin.TabularInline):
    model = Rede
    extra = 1  # Número inicial de campos exibidos


class EquipamentoEmpresaFilter(SimpleListFilter):
    """Filtro personalizado para exibir apenas equipamentos das empresas do usuário"""
    title = "Equipamento"
    parameter_name = "equipamento"

    def lookups(self, request, model_admin):
        if request.user.is_superuser:
            equipamentos = Equipamento.objects.all()
        else:
            empresas_usuario = request.user.empresas.all()
            equipamentos = Equipamento.objects.filter(empresa__in=empresas_usuario)

        return [(equip.id, equip.nome) for equip in equipamentos]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(equipamento__id=self.value())
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
            return queryset.filter(empresa__id=self.value())
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

        return (EmpresaUsuarioFilter, 'pop')  # Usuário comum vê apenas as empresas permitidas



@admin.register(RackEquipamento)
class RackEquipamentoAdmin(admin.ModelAdmin):
    form = RackEquipamentoForm  # Usa o formulário com validação
    list_display = ('rack', 'equipamento', 'us_inicio', 'us_fim', 'lado')
    list_filter = ('rack', 'lado')
    search_fields = ('rack__nome', 'equipamento__nome')
    ordering = ('rack', 'us_inicio')
    autocomplete_fields = ('rack', 'equipamento')

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

    def get_list_filter(self, request):
        """Aplica filtros personalizados para exibir apenas dados acessíveis ao usuário"""
        if request.user.is_superuser:
            return ('rack', 'lado')  # Superusuário vê tudo

        return (EquipamentoEmpresaFilter, 'rack', 'lado')  # Usuário comum vê apenas os equipamentos e racks da empresa


class LoteForm(forms.Form):
    nome_base = forms.CharField(label="Nome Base", max_length=100)
    inicio = forms.IntegerField(label="Número Inicial", min_value=1)
    quantidade = forms.IntegerField(label="Quantidade", min_value=1)
    equipamento = forms.ModelChoiceField(
        queryset=Equipamento.objects.all(),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'empresa' in self.data:  # Se a empresa for selecionada
            try:
                empresa_id = int(self.data.get('empresa'))
                self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa_id=empresa_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:  # Se for um registro existente
            self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa=self.instance.empresa)


class BlocoIPAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'equipamento', 'bloco_cidr', 'next_hop', 'descricao', 'parent', 'criado_em')
    search_fields = ('bloco_cidr', 'empresa__nome', 'equipamento__nome')
    list_filter = ('empresa', 'equipamento')
    form = BlocoIPForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(empresa__usuarios=request.user)

    # Filtrar o campo empresa para mostrar apenas as empresas do usuário logado
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "empresa" and not request.user.is_superuser:
            kwargs["queryset"] = Empresa.objects.filter(usuarios=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(EnderecoIP)
class EnderecoIPAdmin(admin.ModelAdmin):
    list_display = ('bloco', 'ip', 'equipamento', 'next_hop', 'finalidade', 'criado_em')
    search_fields = ('ip', 'equipamento__nome', 'bloco__bloco_cidr')
    list_filter = ('bloco__empresa', 'equipamento')


@admin.register(Porta)
class PortaAdmin(admin.ModelAdmin):
    form = PortaForm
    list_display = ('nome', 'equipamento', 'conexao', 'speed', 'tipo')
    search_fields = ('nome', 'equipamento__nome', 'conexao__nome')
    list_filter = (EmpresaFilter, 'equipamento', 'speed', 'tipo')

    change_list_template = "admin/porta_changelist.html"  # Personalizamos o template

    # Incluímos o URL da ação personalizada
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("adicionar-lote/", self.admin_site.admin_view(self.adicionar_lote), name="adicionar_lote"),
        ]
        return custom_urls + urls

    # Lógica para criar portas em lote
    def adicionar_lote(self, request):
        if request.method == "POST":
            form = LoteForm(request.POST)
            if form.is_valid():
                nome_base = form.cleaned_data["nome_base"]
                inicio = form.cleaned_data["inicio"]
                quantidade = form.cleaned_data["quantidade"]
                equipamento = form.cleaned_data["equipamento"]
                tipo = form.cleaned_data["tipo"]
                speed = form.cleaned_data["speed"]

                portas_criadas = []
                for i in range(inicio, inicio + quantidade):
                    porta_nome = f"{nome_base}{i}"
                    porta = Porta(
                        nome=porta_nome,
                        equipamento=equipamento,
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
            form = LoteForm()

        context = {
            "form": form,
            "opts": self.model._meta,
        }
        return render(request, "admin/adicionar_lote.html", context)


    def get_fields(self, request, obj=None):
        """Reordena os campos para exibir 'empresa' primeiro."""
        fields = super().get_fields(request, obj)
        if 'empresa' in fields:
            fields.remove('empresa')
            fields.insert(0, 'empresa')  # Coloca 'empresa' como o primeiro campo
        return fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            # Passar a empresa para o formulário
            form.base_fields['empresa'].initial = obj.equipamento.empresa
        return form



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
admin_site.register(Rack, RackAdmin)
admin_site.register(RackEquipamento, RackEquipamentoAdmin)
admin_site.register(MaquinaVirtual, MaquinaVirtualAdmin)



# Em vez de usar admin.site, agora usamos admin_site
# Para fazer isso funcionar, você precisará alterar as URLs do seu projeto Django para usar o custom_admin

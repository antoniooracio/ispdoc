from django.contrib import admin, messages
from django import forms
from django.urls import path
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import Group, User
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.admin import AdminSite
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from .forms import PortaForm, RackForm, RackEquipamentoForm
from .views import mapa, mapa_racks
from django.contrib.admin import SimpleListFilter
from .models import Empresa, Pop, Fabricante, Modelo, Equipamento, Porta, BlocoIP, EnderecoIP, Rack, RackEquipamento, MaquinaVirtual, Disco, Rede
import json

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
    search_fields = ('rack__nome', 'equipamento__nome')
    ordering = ('rack', 'us_inicio')
    autocomplete_fields = ('rack', 'equipamento')

    def get_list_filter(self, request):
        """Aplica filtros personalizados para exibir apenas dados acessíveis ao usuário"""
        if request.user.is_superuser:
            return ('rack', 'lado')  # Superusuário vê tudo

        return (EquipamentoEmpresaFilter, RackEmpresaFilter, 'lado')  # Usuário comum vê apenas racks e equipamentos da empresa

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'empresa' in self.data:  # Se a empresa for selecionada dinamicamente
            try:
                empresa_id = int(self.data.get('empresa'))
                self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa_id=empresa_id)
                self.fields['parent'].queryset = BlocoIP.objects.filter(empresa_id=empresa_id)  # Filtro para parent
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:  # Se for um registro existente
            self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa=self.instance.empresa)
            self.fields['parent'].queryset = BlocoIP.objects.filter(empresa=self.instance.empresa)  # Filtro para parent


@admin.register(BlocoIP)
class BlocoIPAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'equipamento', 'bloco_cidr', 'next_hop', 'descricao', 'parent', 'criado_em')
    search_fields = ('bloco_cidr', 'empresa__nome', 'equipamento__nome')
    form = BlocoIPForm

    def get_list_filter(self, request):
        """Aplica filtros personalizados de empresa e equipamento"""
        if request.user.is_superuser:
            return ('empresa', 'equipamento', 'parent')  # Superusuário vê todos os filtros

        return (EmpresaUsuarioFilter, EquipamentoEmpresaFilter)  # Usuário comum vê apenas seus dados

    def get_queryset(self, request):
        """ Lista apenas os blocos de IP das empresas do usuário """
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(empresa__usuarios=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """ Filtra as opções disponíveis ao cadastrar ou editar """
        if not request.user.is_superuser:
            if db_field.name == "empresa":
                kwargs["queryset"] = Empresa.objects.filter(usuarios=request.user)
            elif db_field.name == "equipamento":
                kwargs["queryset"] = Equipamento.objects.filter(empresa__usuarios=request.user)
            elif db_field.name == "parent":  # Filtro para Parent
                kwargs["queryset"] = BlocoIP.objects.filter(empresa__usuarios=request.user)

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
    list_filter = (EmpresaUsuarioFilter, EquipamentoEmpresaFilter, 'speed', 'tipo')


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

import ipaddress
from django.utils.safestring import mark_safe
from django.core.exceptions import ValidationError
from dal import autocomplete
from django import forms
from django.contrib.auth.models import User
from .models import Porta, Empresa, Equipamento, Rack, RackEquipamento, MaquinaVirtual, EnderecoIP, BlocoIP, Vlan
from django import forms
from ipaddress import ip_address, ip_network
from .models import EnderecoIP, BlocoIP

class EnderecoIPForm(forms.ModelForm):
    class Meta:
        model = EnderecoIP
        fields = ['bloco', 'equipamento', 'porta', 'ip', 'finalidade', 'next_hop', 'is_gateway']

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user:
            if user.is_superuser:
                self.fields['bloco'].queryset = BlocoIP.objects.all().order_by('bloco_cidr')
                self.fields['equipamento'].queryset = Equipamento.objects.all().order_by('nome')
            else:
                empresas_usuario = Empresa.objects.filter(usuarios=user)
                self.fields['bloco'].queryset = BlocoIP.objects.filter(empresa__in=empresas_usuario).order_by(
                    'bloco_cidr')
                self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa__in=empresas_usuario).order_by(
                    'nome')

    def clean(self):
        cleaned_data = super().clean()

        if cleaned_data.get('ip') and cleaned_data.get('bloco'):
            ip_obj = ipaddress.ip_address(cleaned_data['ip'])
            rede = ipaddress.ip_network(cleaned_data['bloco'].bloco_cidr, strict=False)
            if ip_obj not in rede:
                raise forms.ValidationError(f"O IP {cleaned_data['ip']} não pertence ao bloco {rede}")

        return cleaned_data


class PasswordWithToggle(forms.PasswordInput):
    template_name = 'widgets/password_with_toggle.html'

    class Media:
        js = ('js/show_password.js',)  # mesmo JS que já criamos


class VlanForm(forms.ModelForm):
    class Meta:
        model = Vlan
        fields = ['empresa', 'equipamento', 'numero', 'nome', 'tipo', 'status']


class CadastrarEnderecosForm(forms.Form):
    equipamento = forms.ModelChoiceField(queryset=Equipamento.objects.none(), required=True)
    porta = forms.ModelChoiceField(queryset=Porta.objects.none(), required=True)
    finalidade = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:
            self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa__in=user.empresas.all())
        else:
            self.fields['equipamento'].queryset = Equipamento.objects.none()

        if 'equipamento' in self.data:
            try:
                equipamento_id = int(self.data.get('equipamento'))
                self.fields['porta'].queryset = Porta.objects.filter(equipamento_id=equipamento_id)
            except (ValueError, TypeError):
                pass
        elif self.initial.get('equipamento'):
            equipamento_id = self.initial.get('equipamento').id
            self.fields['porta'].queryset = Porta.objects.filter(equipamento_id=equipamento_id)

    def get_empresa_do_usuario(self):
        empresa = None
        if self.request and self.request.user.is_authenticated:
            empresa = self.request.user.empresas.first()  # Assumindo que usuário tenha apenas uma empresa
        return empresa

    def clean(self):
        cleaned_data = super().clean()
        bloco = cleaned_data.get('bloco')  # Aqui precisa ver se você tem um campo 'bloco' mesmo

        # Validação para impedir cadastro em bloco subdividido
        if bloco and bloco.subdividido:
            raise ValidationError('Não é permitido cadastrar IP em blocos subdivididos.')

        return cleaned_data

    def as_custom(self):
        fields = []
        for field in self:
            fields.append(f"""
            <div class="form-group field-{field.name}">
                <div class="row">
                    <div class="col-sm-3 text-left">
                        <label for="{field.id_for_label}">{field.label}</label>
                    </div>
                    <div class="col-sm-7">
                        {field.as_widget()}
                    </div>
                </div>
            </div>
            """)
        return ''.join(fields)


class LoteForm(forms.Form):
    empresa = forms.ModelChoiceField(queryset=Empresa.objects.none(), required=True, label="Empresa")
    equipamento = forms.ModelChoiceField(queryset=Equipamento.objects.none(), required=True, label="Equipamento")
    nome_base = forms.CharField(max_length=100, required=True, label="Nome Base")
    inicio = forms.IntegerField(required=True, label="Número Inicial")
    quantidade = forms.IntegerField(required=True, label="Quantidade")
    tipo = forms.CharField(max_length=50, required=True, label="Tipo")
    speed = forms.CharField(max_length=50, required=True, label="Velocidade")

    def __init__(self, *args, **kwargs):
        request = kwargs.pop("request", None)
        super().__init__(*args, **kwargs)

        if request:
            self.fields["empresa"].queryset = Empresa.objects.filter(usuario=request.user).order_by('nome')
            self.fields["equipamento"].queryset = Equipamento.objects.all().order_by('nome')


class EquipamentoForm(forms.ModelForm):
    senha = forms.CharField(
        widget=PasswordWithToggle(render_value=True, attrs={'id': 'id_senha_field'}),
        required=False,  # Permite que o campo fique em branco, caso não deseje alterar a senha
    )

    class Meta:
        model = Equipamento
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        user_is_senha = False
        if self.request and self.request.user.groups.filter(name='Senha').exists():
            user_is_senha = True

        # Adiciona essa info ao atributo do widget
        self.fields['senha'].widget.attrs['user_is_senha'] = user_is_senha

        if not user_is_senha:
            self.fields['senha'].widget.attrs['readonly'] = True

    def clean_senha(self):
        senha = self.cleaned_data.get('senha')
        if not senha and self.instance:
            return self.instance.senha  # mantém a senha antiga
        return senha


class MaquinaVirtualForm(forms.ModelForm):
    senha = forms.CharField(
        widget=PasswordWithToggle(render_value=True, attrs={'id': 'id_senha_field'}),
        required=False,  # Permite que o campo fique em branco, caso não deseje alterar a senha
    )

    class Meta:
        model = MaquinaVirtual
        fields = ['empresa', 'nome', 'equipamento', 'memoria', 'num_processadores',
                  'num_cores', 'sistema_operacional', 'tipo_acesso', 'porta', 'usuario', 'senha']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        user_is_senha = False
        if self.request and self.request.user.groups.filter(name='Senha').exists():
            user_is_senha = True

        # Adiciona essa info ao atributo do widget
        self.fields['senha'].widget.attrs['user_is_senha'] = user_is_senha

        if not user_is_senha:
            self.fields['senha'].widget.attrs['readonly'] = True

    def clean_senha(self):
        senha = self.cleaned_data.get('senha')
        if not senha and self.instance:
            return self.instance.senha  # Mantém a senha atual se não for alterada
        return senha


class EmpresaForm(forms.ModelForm):
    usuarios = forms.ModelMultipleChoiceField(
        queryset=User.objects.all().order_by('username'),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Empresa
        fields = ['nome', 'endereco', 'cidade', 'estado', 'telefone', 'cpf_cnpj', 'representante', 'email', 'status',
                  'usuarios']


class PortaForm(forms.ModelForm):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.none(),
        required=True,
        label="Empresa",
    )

    # Novo campo para "Equipamento de Conexão"
    equipamento_conexao = forms.ModelChoiceField(
        queryset=Equipamento.objects.none(),  # Ajuste conforme seu modelo de Equipamento
        required=False,  # Não é necessário para salvar
        label="Equipamento de Conexão",
    )

    class Meta:
        model = Porta
        fields = '__all__'
        widgets = {
            'equipamento': autocomplete.ModelSelect2(
                url='equipamento-autocomplete',
                forward=['empresa'],
            ),
            'conexao': autocomplete.ModelSelect2(
                url='porta-autocomplete',
                forward=['equipamento_conexao'],  # Filtro agora será baseado no "Equipamento de Conexão"
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.is_authenticated:
            self.fields['empresa'].queryset = Empresa.objects.filter(usuarios=self.request.user).order_by('nome')

        empresa_selecionada = self.initial.get('empresa') or self.data.get('empresa')
        if empresa_selecionada:
            self.fields['empresa'].queryset = Empresa.objects.filter(id=empresa_selecionada).order_by('nome')
            self.fields['empresa'].initial = empresa_selecionada

            # Filtra os equipamentos de conexão com base na empresa selecionada
            self.fields['equipamento_conexao'].queryset = Equipamento.objects.filter(empresa=empresa_selecionada)

        # Corrigindo o filtro do campo 'conexao' para garantir que ele está pegando as portas do 'equipamento_conexao'
        #equipamento_conexao = self.initial.get('equipamento') or self.data.get('equipamento')
        #if equipamento_conexao:
        #    self.fields['conexao'].queryset = Porta.objects.filter(equipamento=equipamento_conexao)

    def clean(self):
        cleaned_data = super().clean()
        conexao = cleaned_data.get('conexao')
        equipamento = cleaned_data.get('equipamento')

        if conexao and equipamento and conexao.equipamento == equipamento:
            raise forms.ValidationError("A porta de conexão não pode pertencer ao mesmo equipamento.")

        if conexao and conexao.pk is None:
            raise forms.ValidationError("A porta de conexão precisa estar salva antes de ser usada.")

        return cleaned_data


class RackForm(forms.ModelForm):
    class Meta:
        model = Rack
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        empresa = cleaned_data.get('empresa')
        pop = cleaned_data.get('pop')

        if pop and empresa and pop.empresa != empresa:
            raise forms.ValidationError("O POP precisa pertencer à mesma empresa.")

        return cleaned_data


class RackEquipamentoForm(forms.ModelForm):
    class Meta:
        model = RackEquipamento
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        rack = cleaned_data.get('rack')
        equipamento = cleaned_data.get('equipamento')
        us_inicio = cleaned_data.get('us_inicio')
        us_fim = cleaned_data.get('us_fim')
        lado = cleaned_data.get('lado')

        if rack and equipamento and rack.empresa != equipamento.empresa:
            raise forms.ValidationError("O equipamento deve pertencer à mesma empresa do Rack.")

        if rack and us_fim > rack.us:
            raise forms.ValidationError("A alocação ultrapassa os Us do Rack.")

        conflitos = RackEquipamento.objects.filter(
            rack=rack,
            lado=lado,
            us_inicio__lte=us_fim,
            us_fim__gte=us_inicio
        ).exclude(id=self.instance.id)

        if conflitos.exists():
            raise forms.ValidationError(f"Os Us {us_inicio}-{us_fim} já estão ocupados no lado {lado}.")

        return cleaned_data
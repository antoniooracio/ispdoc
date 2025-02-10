from dal import autocomplete
from django import forms
from django.contrib.auth.models import User
from .models import Porta, Empresa, Equipamento, Rack, RackEquipamento, MaquinaVirtual


class MaquinaVirtualForm(forms.ModelForm):
    class Meta:
        model = MaquinaVirtual
        fields = ['empresa', 'nome', 'equipamento', 'memoria', 'num_processadores',
                  'num_cores', 'sistema_operacional', 'tipo_acesso', 'porta', 'usuario', 'senha']
        widgets = {
            'senha': forms.PasswordInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar apenas equipamentos do tipo "VMWARE"
        self.fields['equipamento'].queryset = Equipamento.objects.filter(tipo="VMWARE")


class EmpresaForm(forms.ModelForm):
    usuarios = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # Lista de checkboxes para múltiplos usuários
        required=False
    )

    class Meta:
        model = Empresa
        fields = ['nome', 'endereco', 'cidade', 'estado', 'telefone', 'cpf_cnpj', 'representante', 'email', 'status', 'usuarios']


class PortaForm(forms.ModelForm):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.none(),
        required=True,
        label="Empresa",
    )

    class Meta:
        model = Porta
        fields = '__all__'
        widgets = {
            'equipamento': autocomplete.ModelSelect2(
                url='equipamento-autocomplete',
                forward=['empresa'],  # Filtra equipamentos pela empresa
            ),
            'conexao': autocomplete.ModelSelect2(
                url='porta-autocomplete',
                forward=['empresa'],  # Filtra conexões pela empresa
            ),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)  # Obtém o request
        super().__init__(*args, **kwargs)

        if self.request and self.request.user.is_authenticated:
            # Filtra apenas as empresas que o usuário tem acesso
            self.fields['empresa'].queryset = Empresa.objects.filter(usuarios=self.request.user)

        # Se uma empresa já estiver selecionada, filtra os equipamentos dela
        empresa_selecionada = self.initial.get('empresa') or self.data.get('empresa')
        if empresa_selecionada:
            self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa=empresa_selecionada)
        else:
            self.fields['equipamento'].queryset = Equipamento.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        conexao = cleaned_data.get('conexao')

        if conexao and conexao.pk is None:
            raise forms.ValidationError("A porta de conexão precisa estar salva antes de ser usada.")
        return cleaned_data


class RackForm(forms.ModelForm):
    class Meta:
        model = Rack
        fields = '__all__'  # Todos os campos do modelo

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
        fields = '__all__'  # Todos os campos do modelo

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

        # Validação para evitar alocação duplicada
        conflitos = RackEquipamento.objects.filter(
            rack=rack,
            lado=lado,
            us_inicio__lte=us_fim,
            us_fim__gte=us_inicio
        ).exclude(id=self.instance.id)  # Exclui o próprio objeto ao editar

        if conflitos.exists():
            raise forms.ValidationError(f"Os Us {us_inicio}-{us_fim} já estão ocupados no lado {lado}.")

        return cleaned_data
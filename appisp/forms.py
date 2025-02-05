from dal import autocomplete
from django import forms
from .models import Porta, Empresa, Equipamento, Rack, RackEquipamento

class PortaForm(forms.ModelForm):
    empresa = forms.ModelChoiceField(
        queryset=Empresa.objects.all(),
        required=False,
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
        super().__init__(*args, **kwargs)
        # Filtra os equipamentos e portas pelo campo empresa
        if 'empresa' in self.initial:
            empresa = self.initial['empresa']
            self.fields['equipamento'].queryset = Equipamento.objects.filter(empresa=empresa)
            self.fields['conexao'].queryset = Porta.objects.filter(equipamento__empresa=empresa)

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
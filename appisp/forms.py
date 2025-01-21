from dal import autocomplete
from django import forms
from .models import Porta, Empresa, Equipamento




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
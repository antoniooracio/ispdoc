from rest_framework import serializers
# Importando os modelos corretos que voce enviou
from .models import Equipamento, Empresa, BlocoIP

class BlocoIPSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlocoIP
        fields = ['bloco_cidr']



# --- Serializer para o modelo Empresa ---
# Este serializer define quais campos da sua Empresa serao expostos na API.
class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        # Lista de campos que o script de alerta precisa: nome, representante e telefone.
        # Adicionei 'id' e 'email' que podem ser uteis.
        fields = ['id', 'nome', 'representante', 'telefone', 'email']


# --- Serializer para o modelo Equipamento (com as correcoes) ---
# O nome da classe foi corrigido para corresponder ao modelo.
class EquipamentoSerializer(serializers.ModelSerializer):
    # CORRECAO 1: O campo no modelo Equipamento se chama 'empresa' (minusculo).
    # CORRECAO 2: O nome do serializer que estamos usando e 'EmpresaSerializer'.
    # Esta linha aninha os dados da EmpresaSerializer dentro do EquipamentoSerializer.
    empresa = EmpresaSerializer(read_only=True)

    class Meta:
        model = Equipamento
        # '__all__' e a escolha certa aqui. Ele vai incluir todos os campos
        # do modelo Equipamento e tambem o objeto 'empresa' que definimos acima.
        fields = '__all__'

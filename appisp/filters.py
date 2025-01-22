from django.contrib.admin import SimpleListFilter
from django import forms
from .models import Equipamento, Porta


class MultipleEquipamentoFilter(SimpleListFilter):
    title = 'Equipamentos'
    parameter_name = 'equipamento'

    def lookups(self, request, model_admin):
        """
        Retorna uma lista de opções para o filtro.
        """
        equipamentos = Equipamento.objects.all()
        return [(equip.id, equip.nome) for equip in equipamentos]

    def queryset(self, request, queryset):
        """
        Aplica o filtro baseado na seleção do usuário.
        """
        if self.value():
            ids = self.value().split(',')
            return queryset.filter(equipamento__id__in=ids)
        return queryset


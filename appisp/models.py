from django.db import models
from ipaddress import ip_network
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User  # Importe o modelo de usuário
import ipaddress

# Modelo de Empresa
class Empresa(models.Model):
    STATUS_CHOICES = [
        ('ATIVA', 'Ativa'),
        ('INATIVA', 'Inativa'),
    ]

    id = models.AutoField(primary_key=True)
    nome = models.CharField(max_length=255)
    endereco = models.TextField()
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=2)  # Use siglas como "SP", "RJ", etc.
    telefone = models.CharField(max_length=20)
    cpf_cnpj = models.CharField(max_length=18, unique=True)
    representante = models.CharField(max_length=255)
    email = models.EmailField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='ATIVA')
    usuarios = models.ManyToManyField(User, related_name='empresas')  # Adicionando a relação

    def __str__(self):
        return self.nome


# Modelo de POP
class Pop(models.Model):
    nome = models.CharField(max_length=255)
    endereco = models.TextField()
    cidade = models.CharField(max_length=100)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Vincular à Empresa

    def __str__(self):
        return self.nome


# Modelo de Fabricante
class Fabricante(models.Model):
    nome = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.nome


# Modelo de Modelo (associado ao Fabricante)
class Modelo(models.Model):
    modelo = models.CharField(max_length=255)
    fabricante = models.ForeignKey(Fabricante, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Equipamentos modelo"

    def __str__(self):
        return f"{self.fabricante.nome} - {self.modelo}"


# Modelo de Equipamento
class Equipamento(models.Model):
    PROTOCOLO_CHOICES = [
        ('SSH', 'SSH'),
        ('TELNET', 'Telnet'),
        ('WEB', 'Web'),
    ]

    nome = models.CharField(max_length=255)
    ip = models.GenericIPAddressField()
    usuario = models.CharField(max_length=255)
    senha = models.CharField(max_length=255)
    porta = models.PositiveIntegerField()
    protocolo = models.CharField(max_length=10, choices=PROTOCOLO_CHOICES)
    pop = models.ForeignKey(Pop, on_delete=models.CASCADE)  # Vincular ao POP
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Vincular à Empresa
    fabricante = models.ForeignKey(Fabricante, on_delete=models.CASCADE)
    modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE)
    x = models.FloatField(default=20.5)  # Posição X no mapa
    y = models.FloatField(default=30.5)  # Posição Y no mapa
    tipo = models.CharField(
        max_length=50,
        choices=[('Switch', 'Switch'), ('Roteador', 'Roteador'), ('Servidor', 'Servidor'),
                 ('VMWARE', 'VMWARE'), ('AccesPoint', 'AccesPoint'), ('Passivo', 'Passivo')],
        default='Switch'
    )  # Tipo do equipamento (ex: Switch, Roteador)
    status = models.CharField(
        max_length=20,
        choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')],
        default='Ativo'
    )
    observacao = models.TextField()


    def __str__(self):
        return f"{self.nome} ({self.ip})"


# Modelo de Porta
class Porta(models.Model):
    SPEED_CHOICES = [
        ('100M', '100 Mbps'),
        ('1G', '1 Gbps'),
        ('10G', '10 Gbps'),
        ('25G', '25 Gbps'),
        ('40G', '40 Gbps'),
        ('100G', '100 Gbps'),
    ]

    TIPO_CHOICES = [
        ('Eletrico', 'Elétrico'),
        ('Fibra', 'Fibra'),
        ('Radio', 'Rádio'),
    ]

    empresa = models.ForeignKey(
        'Empresa', on_delete=models.CASCADE, related_name='portas', null=True, blank=True
    )
    nome = models.CharField(max_length=50)
    equipamento = models.ForeignKey(
        'Equipamento', on_delete=models.CASCADE, related_name='portas'
    )
    conexao = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conexao_inversa'
    )
    speed = models.CharField(max_length=10, choices=SPEED_CHOICES, default='1G')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='Fibra')
    observacao = models.TextField(
        help_text="Para formatar o texto, use <br> para quebra de linha, <strong>Negrito</strong> para negrito."
    )

    class Meta:
        verbose_name_plural = "Equipamentos porta"

    def save(self, *args, **kwargs):
        # Armazena o estado anterior da conexão para comparação
        if self.pk:
            porta_atual = Porta.objects.filter(pk=self.pk).first()
            conexao_anterior = porta_atual.conexao if porta_atual else None
        else:
            conexao_anterior = None

        super().save(*args, **kwargs)

        # Se a porta está conectada a outra porta
        if self.conexao:
            if self.conexao.conexao != self:
                self.conexao.conexao = self
                self.conexao.save(update_fields=['conexao'])  # Evita chamar save() completamente e recursivamente

        # Se a conexão foi removida, limpa a conexão inversa
        if conexao_anterior and conexao_anterior != self.conexao:
            conexao_anterior.conexao = None
            conexao_anterior.save(update_fields=['conexao'])

    def __str__(self):
        return f"{self.nome} ({self.equipamento.nome} - {self.speed} - {self.tipo})"


# Modelo para Blocos de IP e CIDR
class BlocoIP(models.Model):
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name='blocos_ip')
    bloco_cidr = models.CharField(max_length=18)  # Exemplo: "10.0.0.0/23"
    descricao = models.CharField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_blocos')
    equipamento = models.ForeignKey('Equipamento', on_delete=models.CASCADE, related_name='blocos', null=True, blank=True)
    next_hop = models.GenericIPAddressField(blank=True, null=True)  # Roteamento do bloco
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Blocos de IP"

    def clean(self):
        # Verifica se o equipamento pertence à mesma empresa do bloco
        if self.equipamento.empresa != self.empresa:
            raise ValidationError("O bloco de IP só pode ser cadastrado em um equipamento da mesma empresa.")

    def clean(self):
        bloco = ipaddress.ip_network(self.bloco_cidr, strict=False)

        # 1. Se tiver parent, garantir que o bloco está dentro do parent
        if self.parent:
            parent_bloco = ipaddress.ip_network(self.parent.bloco_cidr, strict=False)

            if not bloco.subnet_of(parent_bloco):
                raise ValidationError(f"O bloco {self.bloco_cidr} não está dentro de {self.parent.bloco_cidr}.")

        # 2. Evitar sobreposição com blocos **sem Parent** (blocos raiz da mesma empresa)
        overlapping = BlocoIP.objects.filter(empresa=self.empresa, parent__isnull=True).exclude(id=self.id)

        for existing in overlapping:
            existing_bloco = ipaddress.ip_network(existing.bloco_cidr, strict=False)

            # Se não houver Parent, impedir sobreposição
            if not self.parent and bloco.overlaps(existing_bloco):
                raise ValidationError(f"O bloco {self.bloco_cidr} se sobrepõe com {existing.bloco_cidr}.")

        # 3. Se o bloco tem um parent, verificar se há sobreposição entre irmãos
        if self.parent:
            siblings = BlocoIP.objects.filter(parent=self.parent).exclude(id=self.id)

            for sibling in siblings:
                sibling_bloco = ipaddress.ip_network(sibling.bloco_cidr, strict=False)
                if bloco.overlaps(sibling_bloco):
                    raise ValidationError(
                        f"O bloco {self.bloco_cidr} se sobrepõe com outro bloco irmão ({sibling.bloco_cidr}).")

        # 4. Verificar se o parent pertence à mesma empresa
        if self.parent and self.parent.empresa != self.empresa:
            raise ValidationError(
                f"O bloco {self.bloco_cidr} pertence à empresa {self.empresa.nome}, mas o parent {self.parent.bloco_cidr} pertence à empresa {self.parent.empresa.nome}. Não é possível associá-los.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bloco_cidr} - {self.empresa.nome} ({self.equipamento.nome if self.equipamento else 'Sem equipamento'})"


# Modelo de Endereçamento IP específico
class EnderecoIP(models.Model):
    bloco = models.ForeignKey(BlocoIP, on_delete=models.CASCADE, related_name='enderecos')
    ip = models.GenericIPAddressField()
    equipamento = models.ForeignKey('Equipamento', on_delete=models.CASCADE, related_name='ips')
    finalidade = models.TextField(blank=True, null=True)
    next_hop = models.GenericIPAddressField(blank=True, null=True)  # Roteamento do IP
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('bloco', 'ip', 'equipamento')  # Evita repetição de IPs no mesmo equipamento

    def clean(self):
        # Verifica se o IP pertence ao bloco
        bloco_rede = ipaddress.ip_network(self.bloco.bloco_cidr, strict=False)
        ip_address = ipaddress.ip_address(self.ip)

        if ip_address not in bloco_rede:
            raise ValidationError(f"O IP {self.ip} não pertence ao bloco {self.bloco.bloco_cidr}.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.ip} - {self.equipamento.nome}"


# Modelo de Rack
class Rack(models.Model):
    nome = models.CharField(max_length=255)
    pop = models.ForeignKey(Pop, on_delete=models.CASCADE)  # Rack pertence a um POP
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Rack pertence a uma única empresa
    us = models.PositiveIntegerField(default=20)  # Número total de Us (padrão: 20)
    modelo = models.CharField(max_length=255, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nome} - {self.pop.nome} ({self.empresa.nome})"

    def save(self, *args, **kwargs):
        # Validação: O POP do Rack deve pertencer à mesma empresa do Rack
        if self.pop.empresa != self.empresa:
            raise ValueError("O POP deve pertencer à mesma empresa do Rack.")
        super().save(*args, **kwargs)


# Modelo de Alocação de Equipamento no Rack
class RackEquipamento(models.Model):
    rack = models.ForeignKey(Rack, on_delete=models.CASCADE, related_name="equipamentos")
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE)
    us_inicio = models.PositiveIntegerField()
    us_fim = models.PositiveIntegerField()
    lado = models.CharField(
        max_length=10,
        choices=[('Frente', 'Frente'), ('Trás', 'Trás')],
        default='Frente'
    )

    class Meta:
        unique_together = ('rack', 'us_inicio', 'lado')  # Garante que um Us no mesmo lado não seja reutilizado

    def save(self, *args, **kwargs):
        # Validação: O equipamento deve pertencer à mesma empresa do Rack
        if self.equipamento.empresa != self.rack.empresa:
            raise ValueError("O equipamento deve pertencer à mesma empresa do Rack.")

        # Validação: A posição final do equipamento não pode ultrapassar os Us do Rack
        if self.us_fim > self.rack.us:
            raise ValueError("O equipamento não pode ser alocado além da capacidade do Rack.")

        # Validação: Não permitir sobreposição de Us no mesmo lado
        conflitos = RackEquipamento.objects.filter(
            rack=self.rack,
            lado=self.lado,
            us_inicio__lte=self.us_fim,
            us_fim__gte=self.us_inicio
        ).exclude(id=self.id)  # Exclui a própria instância ao editar

        if conflitos.exists():
            raise ValueError(f"Os Us {self.us_inicio}-{self.us_fim} já estão ocupados no lado {self.lado}.")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.equipamento.nome} no Rack {self.rack.nome} (Us {self.us_inicio}-{self.us_fim}, {self.lado})"


# Modelo de Maquina Virtual
class MaquinaVirtual(models.Model):
    TIPO_ACESSO_CHOICES = [
        ('SSH', 'SSH'),
        ('TELNET', 'Telnet'),
        ('RDP', 'Área de Trabalho'),
        ('WEB', 'Web'),
    ]

    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)
    nome = models.CharField(max_length=255)
    equipamento = models.ForeignKey(
        'Equipamento',
        on_delete=models.CASCADE,
        limit_choices_to={'tipo': 'VMWARE'},
        related_name='maquinas_virtuais'
    )
    memoria = models.PositiveIntegerField(help_text="Memória em MB")
    num_processadores = models.PositiveIntegerField()
    num_cores = models.PositiveIntegerField()
    sistema_operacional = models.CharField(max_length=255)
    tipo_acesso = models.CharField(max_length=10, choices=TIPO_ACESSO_CHOICES)
    porta = models.PositiveIntegerField()
    usuario = models.CharField(max_length=255)
    senha = models.CharField(max_length=255)


    def __str__(self):
        return f"{self.nome} ({self.empresa})"


class Disco(models.Model):
    maquina = models.ForeignKey(MaquinaVirtual, on_delete=models.CASCADE, related_name="discos")
    tamanho = models.CharField(max_length=50)  # Exemplo: '100GB', '1TB'

    def __str__(self):
        return f"Disco {self.tamanho} - {self.maquina.nome}"


class Rede(models.Model):
    maquina = models.ForeignKey(MaquinaVirtual, on_delete=models.CASCADE, related_name="redes")
    nome = models.CharField(max_length=255)
    ip = models.GenericIPAddressField()

    def __str__(self):
        return f"{self.nome} - {self.ip} ({self.maquina.nome})"
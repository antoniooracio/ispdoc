from django.db import models
from ipaddress import ip_network
from django.core.exceptions import ValidationError
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
    tipo = models.CharField(max_length=50)  # Tipo do equipamento (ex: Switch, Roteador)
    status = models.CharField(
        max_length=20,
        choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')],
        default='Ativo'
    )
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)

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

    nome = models.CharField(max_length=50)  # Ex: "Porta1", "Porta2"
    equipamento = models.ForeignKey('Equipamento', on_delete=models.CASCADE, related_name='portas')
    conexao = models.OneToOneField(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conexao_inversa'
    )
    speed = models.CharField(max_length=10, choices=SPEED_CHOICES, default='1G')  # Valor padrão: 1G
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='Fibra')  # Valor padrão: Fibra
    observacao = models.TextField()


    def save(self, *args, **kwargs):
        # Salvamento inicial da instância atual
        is_new_instance = self.pk is None
        super().save(*args, **kwargs)

        # Se esta porta está conectada a outra porta
        if self.conexao and not is_new_instance:
            if self.conexao.conexao != self:
                self.conexao.conexao = self
                self.conexao.save()
        elif not is_new_instance:
            # Se a conexão foi removida, remove a conexão inversa também
            conexao_inversa = Porta.objects.filter(conexao=self).first()
            if conexao_inversa:
                conexao_inversa.conexao = None
                conexao_inversa.save()

    def __str__(self):
        return f"{self.nome} ({self.equipamento.nome} - {self.speed} - {self.tipo})"

# modelo para Blocos de IP
class BlocoIP(models.Model):
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name='blocos_ip')
    bloco_cidr = models.CharField(max_length=18, unique=True)  # Exemplo: "10.0.0.0/23"
    descricao = models.CharField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_blocos')
    criado_em = models.DateTimeField(auto_now_add=True)

    def clean(self):
        bloco = ipaddress.ip_network(self.bloco_cidr, strict=False)

        # 1. Se o bloco tem um parent, garantir que está dentro do parent
        if self.parent:
            parent_bloco = ipaddress.ip_network(self.parent.bloco_cidr, strict=False)

            if bloco not in parent_bloco.subnets(new_prefix=bloco.prefixlen):
                raise ValidationError(f"O bloco {self.bloco_cidr} não pode ser filho de {self.parent.bloco_cidr}. Deve estar dentro da sub-rede.")

            # 2. Obter todas as sub-redes já cadastradas dentro do parent
            siblings = BlocoIP.objects.filter(parent=self.parent)
            existing_blocks = {ipaddress.ip_network(sibling.bloco_cidr) for sibling in siblings}

            # 3. Gerar todas as sub-redes possíveis dentro do parent
            possible_subnets = set(parent_bloco.subnets(new_prefix=bloco.prefixlen))

            # 4. Criar um conjunto com as sub-redes já ocupadas
            used_subnets = set()
            for existing in existing_blocks:
                used_subnets.update(existing.subnets(new_prefix=existing.prefixlen))

            # 5. Garantir que o novo bloco esteja dentro de um espaço livre
            if bloco not in possible_subnets:
                raise ValidationError(f"O bloco {self.bloco_cidr} não é uma subdivisão válida de {self.parent.bloco_cidr}.")

            if bloco in used_subnets:
                raise ValidationError(f"O bloco {self.bloco_cidr} se sobrepõe com outro bloco já cadastrado.")

        # 6. Verifica se já existe esse bloco na empresa
        if BlocoIP.objects.filter(empresa=self.empresa, bloco_cidr=self.bloco_cidr).exclude(id=self.id).exists():
            raise ValidationError(f"O bloco {self.bloco_cidr} já está cadastrado para esta empresa.")

    def save(self, *args, **kwargs):
        self.clean()  # Chama a validação antes de salvar
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bloco_cidr} - {self.empresa.nome}"


# Modelo de Endereçamento
class EnderecoIP(models.Model):
    bloco = models.ForeignKey(BlocoIP, on_delete=models.CASCADE, related_name='enderecos')
    ip = models.GenericIPAddressField(unique=False)  # Exemplo: "10.0.0.1"
    equipamento = models.CharField(max_length=255, blank=True, null=True)
    finalidade = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('bloco', 'ip')  # Evita que o mesmo IP seja usado duas vezes no mesmo bloco

    def __str__(self):
        return f"{self.ip} - {self.equipamento if self.equipamento else 'Disponível'}"

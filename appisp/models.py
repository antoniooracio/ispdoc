from django.db import models


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
    ip = models.GenericIPAddressField(unique=True)  # Validação automática de IP
    usuario = models.CharField(max_length=255)
    senha = models.CharField(max_length=255)
    porta = models.PositiveIntegerField()
    protocolo = models.CharField(max_length=10, choices=PROTOCOLO_CHOICES)
    pop = models.ForeignKey(Pop, on_delete=models.CASCADE)  # Vincular ao POP
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Vincular à Empresa
    fabricante = models.ForeignKey(Fabricante, on_delete=models.CASCADE)
    modelo = models.ForeignKey(Modelo, on_delete=models.CASCADE)
    x = models.FloatField()  # Posição X no mapa
    y = models.FloatField()  # Posição Y no mapa
    tipo = models.CharField(max_length=50)  # Tipo do equipamento (ex: Switch, Roteador)
    status = models.CharField(
        max_length=20,
        choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')],
        default='Ativo'
    )
    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.nome} ({self.ip})"


# modelo de Porta
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

from django.db import models
from ipaddress import ip_network, ip_address
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User  # Importe o modelo de usuário
import ipaddress
import uuid

from django.utils.html import format_html


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

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class EmpresaToken(models.Model):
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name="token")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return f"{self.empresa.nome} - {self.token}"


# Modelo de POP
class Pop(models.Model):
    nome = models.CharField(max_length=255)
    endereco = models.TextField()
    cidade = models.CharField(max_length=100)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Vincular à Empresa

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


# Modelo de Fabricante
class Fabricante(models.Model):
    nome = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


# Modelo de Modelo (associado ao Fabricante)
class Modelo(models.Model):
    modelo = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True, null=True)
    fabricante = models.ForeignKey(Fabricante, on_delete=models.CASCADE)
    part_number = models.CharField(max_length=255, blank=True, null=True)
    altura = models.IntegerField(blank=True, null=True)
    is_full_depth = models.BooleanField(default=False)
    airflow = models.CharField(max_length=255, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True)

    imagem_frontal = models.ImageField(upload_to='modelos/', blank=True, null=True)
    imagem_traseira = models.ImageField(upload_to='modelos/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Equipamentos modelo"
        ordering = ['modelo']

    def __str__(self):
        return f"{self.fabricante.nome} - {self.modelo}"


# Modelo de Equipamento
class Equipamento(models.Model):
    PROTOCOLO_CHOICES = [
        ('SSH', 'SSH'),
        ('TELNET', 'Telnet'),
        ('WEB', 'Web'),
        ('Winbox', 'Winbox'),
        ('Remoto', 'Remoto')
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
                 ('VMWARE', 'VMWARE'), ('AccesPoint', 'AccesPoint'), ('Passivo', 'Passivo'),
                 ('Olt', 'Olt'), ('Transporte', 'Transporte')],
        default='Switch'
    )  # Tipo do equipamento (ex: Switch, Roteador)
    status = models.CharField(
        max_length=20,
        choices=[('Ativo', 'Ativo'), ('Inativo', 'Inativo')],
        default='Ativo'
    )
    observacao = models.TextField()

    class Meta:
        ordering = ['nome']

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
        ('Transporte', 'Transporte'),
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
        help_text="Para Formata o texto, use < /br> quebra de linha, < strong><strong>Negrito</strong>< /strong>, sem espaços"
    )

    class Meta:
        verbose_name_plural = "Equipamentos porta"
        ordering = ['nome']

    def save(self, *args, **kwargs):
        # Armazena o estado anterior da conexão para comparação
        if self.pk:
            porta_atual = Porta.objects.filter(pk=self.pk).first()
            conexao_anterior = porta_atual.conexao if porta_atual else None
        else:
            conexao_anterior = None

        super().save(*args, **kwargs)

        # Armazena a observação da porta atual
        observacao_atual = self.observacao

        # Se a porta está conectada a outra porta (B)
        if self.conexao:
            # Verifica se a observação de A é diferente da de B
            if self.conexao.observacao != observacao_atual:
                # Atualiza a observação da porta conectada (B) com a observação da porta A
                self.conexao.observacao = observacao_atual
                self.conexao.save(update_fields=['observacao'])  # Atualiza somente a observação da porta conectada

        # Se a porta está conectada a outra porta
        if self.conexao:
            if self.conexao.conexao != self:
                self.conexao.conexao = self
                self.conexao.save(update_fields=['conexao'])  # Evita chamar save() completamente e recursivamente

            # Atualiza o tipo e speed da porta conectada, se ela existir
            if self.conexao:  # Verifica se existe uma conexão válida
                if self.speed != self.conexao.speed or self.tipo != self.conexao.tipo:
                    self.conexao.speed = self.speed
                    self.conexao.tipo = self.tipo
                    self.conexao.save(update_fields=['speed', 'tipo'])

        # Se a conexão foi removida, limpa a conexão inversa
        if conexao_anterior and conexao_anterior != self.conexao:
            if conexao_anterior:  # Verifica se a conexão anterior existe antes de tentar acessar
                conexao_anterior.conexao = None
                conexao_anterior.save(update_fields=['conexao'])

        # Se a conexão foi removida, limpa a conexão inversa
        if conexao_anterior and conexao_anterior != self.conexao:
            conexao_anterior.conexao = None
            conexao_anterior.save(update_fields=['conexao'])

    def __str__(self):
        return f"{self.nome} ({self.equipamento.nome} - {self.speed} - {self.tipo})"


# Modelo de VLAN
class Vlan(models.Model):
    STATUS_CHOICES = [
        ('Ativa', 'Ativa'),
        ('Inativa', 'Inativa'),
    ]

    TIPOS_VLAN = [
        ('Acesso', 'Acesso'),
        ('Trunk', 'Trunk'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='vlans')
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name='vlans', null=True, blank=True)
    numero = models.PositiveIntegerField()  # VLAN ID (1-4095)
    nome = models.CharField(max_length=255, blank=True, null=True)
    tipo = models.CharField(max_length=10, choices=TIPOS_VLAN, default='Acesso')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Ativa')

    class Meta:
        ordering = ['numero']
        unique_together = ('empresa', 'numero')  # Garante que o número da VLAN é único dentro da empresa

    def __str__(self):
        return f"VLAN {self.numero} - {self.nome if self.nome else 'Sem nome'} ({self.empresa.nome})"

    def clean(self):
        """ Validações para garantir que a VLAN está dentro do intervalo correto e não existe duplicidade """
        if self.numero < 1 or self.numero > 4095:
            raise ValidationError("O número da VLAN deve estar entre 1 e 4095.")

        if Vlan.objects.filter(empresa=self.empresa, numero=self.numero).exclude(id=self.id).exists():
            raise ValidationError(f"A VLAN {self.numero} já está cadastrada para a empresa {self.empresa.nome}.")


# Modelo para VlanPorta
class VlanPorta(models.Model):
    TIPOS_VLAN_PORTA = [
        ("Access", "Access"),
        ("Trunk", "Trunk"),
        ("Ibrida", "Ibrida"),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="vlan_portas")
    equipamento = models.ForeignKey(Equipamento, on_delete=models.CASCADE, related_name="vlan_portas")
    vlan = models.ForeignKey(Vlan, on_delete=models.CASCADE, related_name="vlan_portas")
    porta = models.ForeignKey(Porta, on_delete=models.CASCADE, related_name="vlan_portas")
    tipo = models.CharField(max_length=10, choices=TIPOS_VLAN_PORTA, default="Access")

    vlan_nativa = models.BooleanField(default=False)  # Se for Trunk, indica se é VLAN nativa
    vlans_permitidas = models.ManyToManyField(Vlan, blank=True, related_name="permitidas_em_portas")

    class Meta:
        unique_together = ("vlan", "porta")  # Evita duplicidade

    def __str__(self):
        return f"VLAN {self.vlan.numero} - {self.porta.nome} ({self.tipo})"

    def clean(self):
        """ Validações antes de salvar """
        if self.tipo == "Access" and self.vlan_nativa:
            raise ValidationError("Uma porta Access não pode ter VLAN nativa.")

    def save(self, *args, **kwargs):
        """ Garante que as regras sejam aplicadas antes e depois de salvar """
        self.clean()  # Aplica validações básicas

        super().save(*args, **kwargs)  # Salva o objeto primeiro (gera um ID)

        # Agora podemos acessar ManyToManyField sem erro
        if self.tipo == "Access":
            self.vlans_permitidas.clear()  # Remove qualquer VLAN permitida

        if self.tipo == "Trunk":
            if not self.vlans_permitidas.exists() and not self.vlans_permitidas:
                raise ValidationError("Uma porta Trunk deve ter VLANs permitidas.")

        # Se for VLAN nativa, ela não pode estar na lista de VLANs permitidas
        if self.vlan_nativa and self.vlan in self.vlans_permitidas.all():
            self.vlans_permitidas.remove(self.vlan)


# Modelo para Blocos de IP e CIDR
class BlocoIP(models.Model):
    TIPO_CHOICES = [
        ('IPv4', 'IPv4'),
        ('IPv6', 'IPv6'),
    ]

    empresa = models.ForeignKey('Empresa', on_delete=models.CASCADE, related_name='blocos_ip')
    tipo_ip = models.CharField(max_length=4, choices=TIPO_CHOICES, default='IPv4')  # Indica se é IPv4 ou IPv6
    bloco_cidr = models.CharField(max_length=50)  # IPv6 precisa de mais espaço
    descricao = models.CharField(max_length=255, blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_blocos')
    equipamento = models.ForeignKey('Equipamento', on_delete=models.CASCADE, related_name='blocos', null=True,
                                    blank=True)
    next_hop = models.GenericIPAddressField(blank=True, null=True)  # Roteamento do bloco
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Blocos de IP"
        ordering = ['bloco_cidr']

    def nivel(self):
        """Quantidade de níveis até a raiz (parent=None)"""
        nivel = 0
        parent = self.parent
        while parent:
            nivel += 1
            parent = parent.parent
        return nivel

    def clean(self):
        """Validações para garantir que o bloco é correto e não se sobrepõe a outros blocos"""
        try:
            bloco = ipaddress.ip_network(self.bloco_cidr, strict=False)
        except ValueError:
            raise ValidationError(f"O bloco {self.bloco_cidr} não é um CIDR válido.")

        # 1. Garante que o tipo (IPv4/IPv6) está correto
        if (bloco.version == 4 and self.tipo_ip != 'IPv4') or (bloco.version == 6 and self.tipo_ip != 'IPv6'):
            raise ValidationError(f"O bloco {self.bloco_cidr} não corresponde ao tipo {self.tipo_ip}.")

        # 2. Se tiver parent, garantir que o bloco está dentro do parent
        if self.parent:
            parent_bloco = ipaddress.ip_network(self.parent.bloco_cidr, strict=False)

            if not bloco.subnet_of(parent_bloco):
                raise ValidationError(f"O bloco {self.bloco_cidr} não está dentro de {self.parent.bloco_cidr}.")

        # 3. Evitar sobreposição com blocos sem Parent (blocos raiz da mesma empresa e do mesmo tipo)
        overlapping = BlocoIP.objects.filter(empresa=self.empresa, parent__isnull=True, tipo_ip=self.tipo_ip).exclude(
            id=self.id)

        for existing in overlapping:
            existing_bloco = ipaddress.ip_network(existing.bloco_cidr, strict=False)
            if not self.parent and bloco.overlaps(existing_bloco):
                raise ValidationError(f"O bloco {self.bloco_cidr} se sobrepõe com {existing.bloco_cidr}.")

        # 4. Se tem parent, verificar sobreposição entre irmãos
        if self.parent:
            siblings = BlocoIP.objects.filter(parent=self.parent).exclude(id=self.id)

            for sibling in siblings:
                sibling_bloco = ipaddress.ip_network(sibling.bloco_cidr, strict=False)
                if bloco.overlaps(sibling_bloco):
                    raise ValidationError(
                        f"O bloco {self.bloco_cidr} se sobrepõe com outro bloco irmão ({sibling_bloco}).")

        # 5. Verificar se o parent pertence à mesma empresa
        if self.parent and self.parent.empresa != self.empresa:
            raise ValidationError(
                f"O bloco {self.bloco_cidr} pertence à empresa {self.empresa.nome}, mas o parent {self.parent.bloco_cidr} pertence a {self.parent.empresa.nome}."
            )

    def sugerir_proximo_ip(self):
        """ Retorna o próximo IP disponível dentro do bloco """
        bloco_rede = ipaddress.ip_network(self.bloco_cidr, strict=False)
        ips_ocupados = set(EnderecoIP.objects.filter(bloco=self).values_list('ip', flat=True))

        for ip in bloco_rede.hosts():  # Percorre todos os IPs disponíveis no bloco
            if str(ip) not in ips_ocupados:
                return str(ip)

        return None  # Se não houver IP disponível

    def network(self):
        return ip_network(self.bloco_cidr, strict=False)

    def subnet(self, new_prefix):
        """Divide este bloco em sub-blocos com o prefixo fornecido."""
        network = self.network()
        return list(network.subnets(new_prefix=new_prefix))

    def total_ips(self):
        """Quantidade de IPs disponíveis no bloco."""
        return self.network().num_addresses

    def save(self, *args, **kwargs):
        if self.equipamento_id is None:
            self.equipamento = None  # Garante que não há valor inválido
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.bloco_cidr} - {self.empresa.nome} ({self.equipamento.nome if self.equipamento else 'Sem equipamento'})"

    def utilizacao_percentual(self):
        """Retorna a porcentagem de utilização do bloco, considerando os IPs de rede e broadcast como utilizados"""
        total = self.total_ips()
        bloco_rede = ipaddress.ip_network(self.bloco_cidr, strict=False)

        # Para blocos /30 e abaixo, considerar os IPs de rede e broadcast como usados
        if bloco_rede.prefixlen <= 30:
            total -= 2  # Subtrai os 2 IPs (rede e broadcast)

        # Contabiliza os IPs ocupados
        usados = self.enderecos.count()

        if total == 0:
            return 0
        return (usados / total) * 100

    from django.utils.html import format_html

    def utilizacao_barra(self):
        """Retorna uma barra de progresso com degradê dinâmico baseado no percentual."""
        percentual = self.utilizacao_percentual()
        percentual_str = f"{percentual:.1f}%"

        # Definindo o degradê baseado no percentual
        if percentual <= 50:
            # Degradê simples verde -> amarelo
            gradiente = "linear-gradient(90deg, limegreen, yellow)"
        elif percentual <= 75:
            # Degradê verde -> amarelo -> vermelho claro
            gradiente = "linear-gradient(90deg, limegreen, yellow, orangered)"
        else:
            # Degradê verde -> amarelo -> vermelho escuro
            gradiente = "linear-gradient(90deg, limegreen, yellow, darkred)"

        return format_html(
            '''
            <div style="position: relative; background-color: #0d0d2b; border-radius: 30px; overflow: hidden; height: 18px; width: 100%; box-shadow: inset 0 0 5px #000;">
                <div style="height: 100%; width: {}%; 
                            background: {}; 
                            transition: width 0.5s;">
                </div>
                <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;
                            display: flex; align-items: center; justify-content: center;
                            color: white; font-weight: bold; font-size: 14px;">
                    {}
                </div>
            </div>
            ''',
            percentual,
            gradiente,
            percentual_str
        )

    utilizacao_barra.short_description = "Utilização"
    utilizacao_barra.allow_tags = True


# Classe para cadastro de IP individual
class EnderecoIP(models.Model):
    bloco = models.ForeignKey('BlocoIP', on_delete=models.CASCADE, related_name='enderecos')
    ip = models.GenericIPAddressField(blank=True, null=True)  # Permite sugestão automática
    equipamento = models.ForeignKey('Equipamento', on_delete=models.CASCADE, related_name='ips')
    porta = models.ForeignKey('Porta', on_delete=models.CASCADE, related_name='ips')

    finalidade = models.TextField(blank=True, null=True)
    next_hop = models.GenericIPAddressField(blank=True, null=True)
    is_gateway = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('bloco', 'ip', 'equipamento')
        ordering = ['ip']

    def clean(self):
        """Validações antes de salvar"""
        if not self.bloco:
            raise ValidationError("O bloco de IP é obrigatório.")

        if not self.equipamento:
            raise ValidationError("O equipamento é obrigatório.")

        if not self.porta:
            raise ValidationError("A porta é obrigatória.")

        if self.porta.equipamento != self.equipamento:
            raise ValidationError("A porta selecionada não pertence ao equipamento escolhido.")

        if not self.ip:
            return  # Se não há IP informado, não realiza validações que dependem dele

        ip_obj = ip_address(self.ip)
        bloco_rede = ip_network(self.bloco.bloco_cidr, strict=False)

        # 🌟 NOVO: Se o bloco está subdividido, impedir cadastro direto nele
        sub_blocos = BlocoIP.objects.filter(parent=self.bloco)  # Assume que seu BlocoIP tem campo 'bloco_pai'
        if sub_blocos.exists():
            # Verifica em qual sub-bloco o IP pertence
            sub_bloco_correto = None
            for sub_bloco in sub_blocos:
                rede_sub = ip_network(sub_bloco.bloco_cidr, strict=False)
                if ip_obj in rede_sub:
                    sub_bloco_correto = sub_bloco
                    break

            if sub_bloco_correto:
                raise ValidationError(
                    f"Este bloco foi subdividido. Cadastre o IP {self.ip} no bloco {sub_bloco_correto.bloco_cidr}."
                )
            else:
                raise ValidationError(
                    f"Este bloco foi subdividido. O IP {self.ip} não pertence a nenhum dos sub-blocos disponíveis."
                )

        # 1️⃣ Validação: O IP pertence ao bloco informado
        if ip_obj not in bloco_rede:
            raise ValidationError(f"O IP {self.ip} não pertence ao bloco {bloco_rede}.")

        # 2️⃣ Validação: IP já cadastrado no bloco
        if EnderecoIP.objects.filter(bloco=self.bloco, ip=self.ip).exclude(id=self.id).exists():
            raise ValidationError(f"O IP {self.ip} já está cadastrado neste bloco.")

        # 3️⃣ Validação: IP de rede e broadcast
        if bloco_rede.version == 4 and bloco_rede.prefixlen <= 30:
            if ip_obj in (bloco_rede.network_address, bloco_rede.broadcast_address):
                raise ValidationError(f"O IP {self.ip} é um endereço de rede ou broadcast e não pode ser usado.")

        if bloco_rede.version == 6 and bloco_rede.prefixlen <= 126:
            if ip_obj in (bloco_rede.network_address, bloco_rede.broadcast_address):
                raise ValidationError(f"O IP {self.ip} é um endereço de rede ou broadcast e não pode ser usado.")

        # 4️⃣ Validação: Apenas um gateway por bloco
        if self.is_gateway:
            if EnderecoIP.objects.filter(bloco=self.bloco, is_gateway=True).exclude(id=self.id).exists():
                raise ValidationError(f"Já existe um gateway para o bloco {self.bloco.bloco_cidr}. Apenas um é permitido.")

            if not self.next_hop:
                raise ValidationError("O campo 'next_hop' é obrigatório para o gateway.")

        super().clean()

    def save(self, *args, **kwargs):
        """Sugere um IP caso não tenha sido fornecido"""
        if not self.ip:
            proximo_ip = self.bloco.sugerir_proximo_ip()
            if not proximo_ip:
                raise ValidationError("Não há IPs disponíveis neste bloco.")
            self.ip = proximo_ip

        self.full_clean()  # Validações completas antes de salvar
        super().save(*args, **kwargs)

    def __str__(self):
        gateway_status = " (Gateway)" if self.is_gateway else ""
        return f"{self.ip} - {self.equipamento.nome} (Porta: {self.porta.nome}){gateway_status}"


# Modelo de Rack
class Rack(models.Model):
    nome = models.CharField(max_length=255)
    pop = models.ForeignKey(Pop, on_delete=models.CASCADE)  # Rack pertence a um POP
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Rack pertence a uma única empresa
    us = models.PositiveIntegerField(default=20)  # Número total de Us (padrão: 20)
    modelo = models.CharField(max_length=255, blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['nome']

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
        ordering = ['equipamento']

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
    observacao = models.TextField(
        help_text="Para Formata o texto, use < /br> quebra de linha, < strong><strong>Negrito</strong>< /strong>, sem espaços")

    class Meta:
        ordering = ['nome']

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


class IntegracaoZabbix(models.Model):
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name='integracao_zabbix'
    )
    url = models.URLField(
        verbose_name='URL da API Zabbix',
        help_text='Ex: http://zabbix.suaempresa.com/api_jsonrpc.php'
    )
    usuario = models.CharField(
        max_length=100,
        verbose_name='Usuário Zabbix',
        help_text='Usuário com permissão de API no Zabbix'
    )
    senha = models.CharField(
        max_length=100,
        verbose_name='Senha Zabbix'
    )
    token = models.CharField("Token de API", max_length=255, blank=True, null=True)
    observacoes = models.TextField(
        blank=True,
        null=True,
        help_text='Informações adicionais da integração'
    )
    ativo = models.BooleanField(
        default=True,
        help_text='Marque para habilitar a integração'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    ultima_sincronizacao = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Data da última sincronização com o Zabbix'
    )

    class Meta:
        verbose_name = 'Integração com Zabbix'
        verbose_name_plural = 'Integrações com Zabbix'
        ordering = ['empresa']

    def __str__(self):
        return f'Zabbix - {self.empresa.nome}'


class IntegracaoNetbox(models.Model):
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name='integracao_netbox'
    )
    url = models.URLField(
        verbose_name='URL da API NetBox',
        help_text='Ex: https://netbox.suaempresa.com/api/'
    )
    token = models.CharField(
        max_length=255,
        verbose_name='Token de API',
        help_text='Token de acesso gerado no NetBox'
    )
    observacoes = models.TextField(
        blank=True,
        null=True,
        help_text='Informações adicionais da integração'
    )
    ativo = models.BooleanField(
        default=True,
        help_text='Marque para habilitar a integração com o NetBox'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    ultima_sincronizacao = models.DateTimeField(
        blank=True,
        null=True,
        help_text='Data da última sincronização com o NetBox'
    )

    class Meta:
        verbose_name = 'Integração com NetBox'
        verbose_name_plural = 'Integrações com NetBox'
        ordering = ['empresa']

    def __str__(self):
        return f'NetBox - {self.empresa.nome}'
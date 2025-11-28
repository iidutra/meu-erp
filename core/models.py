from django.db import models
from decimal import Decimal
from django.db.models import Sum
from django.contrib.auth.models import User

class Empresa(models.Model):
    RAMO_CHOICES = [
        ('GERAL', 'Geral / Outros'),
        ('AUTO', 'Automotivo (lava jato, oficina, etc.)'),
        # no futuro dá pra incluir mais tipos aqui
    ]

    nome_fantasia = models.CharField(max_length=150)
    documento = models.CharField(max_length=20, blank=True, null=True)  # CPF/CNPJ
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    ativo = models.BooleanField(default=True)

    ramo = models.CharField(
        max_length=20,
        choices=RAMO_CHOICES,
        default='GERAL',
    )

    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome_fantasia


class Cliente(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=150)
    documento = models.CharField(max_length=20, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.nome} ({self.empresa.nome_fantasia})'


class Produto(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True, null=True)
    preco_venda = models.DecimalField(max_digits=10, decimal_places=2)
    controla_estoque = models.BooleanField(default=False)
    estoque_atual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text='Use unidades, kg, etc. conforme o negócio.'
    )
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.nome} - {self.empresa.nome_fantasia}'


class Servico(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    nome = models.CharField(max_length=150)
    descricao = models.TextField(blank=True, null=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    duracao_minutos = models.PositiveIntegerField(blank=True, null=True)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.nome} - {self.empresa.nome_fantasia}'


class Orcamento(models.Model):
    STATUS_CHOICES = [
        ('RASCUNHO', 'Rascunho'),
        ('ENVIADO', 'Enviado'),
        ('APROVADO', 'Aprovado'),
        ('RECUSADO', 'Recusado'),
    ]

    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT)
    data = models.DateTimeField(auto_now_add=True)
    validade = models.DateField(blank=True, null=True)
    
    # 👇 NOVOS CAMPOS
    placa = models.CharField(max_length=10, blank=True, null=True)
    veiculo_descricao = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Ex.: SUV prata, Sedan preto, Moto vermelha...'
    )

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='RASCUNHO')
    observacoes = models.TextField(blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f'Orçamento #{self.id} - {self.cliente.nome}'


class OrcamentoItem(models.Model):
    TIPO_ITEM_CHOICES = [
        ('PRODUTO', 'Produto'),
        ('SERVICO', 'Serviço'),
    ]

    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name='itens')
    tipo_item = models.CharField(max_length=8, choices=TIPO_ITEM_CHOICES)
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, blank=True, null=True)
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, blank=True, null=True)
    descricao = models.CharField(max_length=200, blank=True, null=True)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self):
        return f'Item {self.id} - Orçamento #{self.orcamento.id}'


class Documento(models.Model):
    """
    Representa uma Venda ou Ordem de Serviço.
    """
    TIPO_CHOICES = [
        ('VENDA', 'Venda'),
        ('OS', 'Ordem de Serviço'),
    ]

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='documentos'
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='documentos'
    )
     # 👇 COPIA DA INFO DO VEÍCULO DO ORÇAMENTO
    placa = models.CharField(max_length=10, blank=True, null=True)
    veiculo_descricao = models.CharField(max_length=100, blank=True, null=True)

    tipo = models.CharField(max_length=5, choices=TIPO_CHOICES)
    data = models.DateTimeField(auto_now_add=True)
    origem_orcamento = models.ForeignKey(
        Orcamento,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='documentos'
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.get_tipo_display()} #{self.id} - {self.cliente.nome}'

    @property
    def valor_pago(self):
        soma = self.pagamentos.aggregate(total=Sum('valor'))['total']
        return soma or Decimal('0')

    @property
    def saldo(self):
        return self.total - self.valor_pago

    @property
    def status_financeiro(self):
        if self.total == 0:
            return 'Sem valor'
        if self.saldo <= 0:
            return 'Pago'
        if self.valor_pago > 0:
            return 'Parcial'
        return 'Em aberto'
    
class Pagamento(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ('DINHEIRO', 'Dinheiro'),
        ('CARTAO', 'Cartão'),
        ('PIX', 'PIX'),
        ('BOLETO', 'Boleto'),
        ('OUTRO', 'Outro'),
    ]

    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name='pagamentos')
    data = models.DateTimeField(auto_now_add=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    forma_pagamento = models.CharField(max_length=10, choices=FORMA_PAGAMENTO_CHOICES)
    observacoes = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'Pgto {self.id} - {self.documento}'


class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='usuarios')

    def __str__(self):
        return f'{self.user.username} - {self.empresa.nome_fantasia}'
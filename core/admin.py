from django.contrib import admin
from .models import (
    Empresa,
    Cliente,
    Produto,
    Servico,
    Orcamento,
    OrcamentoItem,
    Documento,
    Pagamento,
    Perfil,
)

@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome_fantasia', 'documento', 'email', 'telefone', 'ativo')
    search_fields = ('nome_fantasia', 'documento')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'telefone', 'email')
    search_fields = ('nome', 'documento')
    list_filter = ('empresa',)

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'preco_venda', 'ativo')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome',)

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'empresa', 'preco', 'ativo')
    list_filter = ('empresa', 'ativo')
    search_fields = ('nome',)

@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'empresa', 'cliente', 'data', 'status', 'total')
    list_filter = ('empresa', 'status')
    search_fields = ('cliente__nome',)

@admin.register(OrcamentoItem)
class OrcamentoItemAdmin(admin.ModelAdmin):
    list_display = ('orcamento', 'tipo_item', 'produto', 'servico', 'quantidade', 'preco_unitario', 'total')

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'tipo', 'empresa', 'cliente', 'data', 'total')
    list_filter = ('empresa', 'tipo')

@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ('documento', 'data', 'valor', 'forma_pagamento')

@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'empresa')
    list_filter = ('empresa',)

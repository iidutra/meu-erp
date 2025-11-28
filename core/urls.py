from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    # Clientes
    path('clientes/', views.cliente_list, name='cliente_list'),
    path('clientes/novo/', views.cliente_create, name='cliente_create'),
    path('clientes/<int:pk>/editar/', views.cliente_update, name='cliente_update'),

    # Orçamentos
    path('orcamentos/', views.orcamento_list, name='orcamento_list'),
    path('orcamentos/novo/', views.orcamento_create, name='orcamento_create'),
    path('orcamentos/<int:pk>/', views.orcamento_detail, name='orcamento_detail'),
    path('orcamentos/<int:pk>/converter/', views.orcamento_converter, name='orcamento_converter'),

    # Documentos (Vendas / OS)
    path('documentos/', views.documento_list, name='documento_list'),
    path('documentos/<int:pk>/', views.documento_detail, name='documento_detail'),
    path('documentos/<int:pk>/pagamentos/novo/', views.pagamento_create, name='pagamento_create'),
    
     # Produtos
    path('produtos/', views.produto_list, name='produto_list'),
    path('produtos/novo/', views.produto_create, name='produto_create'),
    path('produtos/<int:pk>/editar/', views.produto_update, name='produto_update'),

    # Serviços
    path('servicos/', views.servico_list, name='servico_list'),
    path('servicos/novo/', views.servico_create, name='servico_create'),
    path('servicos/<int:pk>/editar/', views.servico_update, name='servico_update'),
    
    path('orcamentos/<int:pk>/status/', views.orcamento_set_status, name='orcamento_set_status'),
    path('orcamentos/<int:pk>/duplicar/', views.orcamento_duplicar, name='orcamento_duplicar'),
    
    path('orcamentos/<int:pk>/imprimir/', views.orcamento_print, name='orcamento_print'),

]

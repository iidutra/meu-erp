from decimal import Decimal
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.http import require_POST
from django.db.models import Q

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

from .models import Cliente, Orcamento, OrcamentoItem, Documento, Pagamento, Produto, Servico
from .forms import (
    ClienteForm,
    OrcamentoForm,
    OrcamentoItemFormSet,
    PagamentoForm,
    ProdutoForm,
    ServicoForm,
)

from .utils import get_empresa_from_user

@login_required
def dashboard(request):
    empresa = get_empresa_from_user(request.user)

    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)

    # Documentos da empresa
    documentos_qs = Documento.objects.filter(empresa=empresa)

    # Faturamento do dia
    faturamento_hoje = (
        documentos_qs.filter(data__date=hoje)
        .aggregate(total=Sum('total'))['total'] or Decimal('0')
    )

    # Faturamento do mês
    faturamento_mes = (
        documentos_qs.filter(data__date__gte=inicio_mes, data__date__lte=hoje)
        .aggregate(total=Sum('total'))['total'] or Decimal('0')
    )

    # OS em aberto (saldo > 0) – vamos contar em Python mesmo
    ordens_servico = documentos_qs.filter(tipo='OS')
    os_abertas = [d for d in ordens_servico if d.saldo > 0]
    qtd_os_abertas = len(os_abertas)

    # Orçamentos “em andamento” (status diferente de Recusado)
    orcamentos_qs = Orcamento.objects.filter(empresa=empresa)
    orcamentos_abertos = orcamentos_qs.exclude(status='RECUSADO')
    qtd_orcamentos_abertos = orcamentos_abertos.count()

    # Últimos registros para tabelas
    ultimos_orcamentos = (
        orcamentos_qs.select_related('cliente')
        .order_by('-data')[:5]
    )
    ultimos_documentos = (
        documentos_qs.select_related('cliente')
        .order_by('-data')[:5]
    )

    contexto = {
        'empresa': empresa,
        'faturamento_hoje': faturamento_hoje,
        'faturamento_mes': faturamento_mes,
        'qtd_os_abertas': qtd_os_abertas,
        'qtd_orcamentos_abertos': qtd_orcamentos_abertos,
        'ultimos_orcamentos': ultimos_orcamentos,
        'ultimos_documentos': ultimos_documentos,
    }
    return render(request, 'core/dashboard.html', contexto)


# --------- CLIENTES ---------
@login_required
def cliente_list(request):
    empresa = get_empresa_from_user(request.user)
    clientes = Cliente.objects.filter(empresa=empresa).order_by('nome')
    return render(request, 'core/cliente_list.html', {'clientes': clientes})


@login_required
def cliente_create(request):
    empresa = get_empresa_from_user(request.user)

    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            cliente = form.save(commit=False)
            cliente.empresa = empresa
            cliente.save()
            messages.success(request, 'Cliente criado com sucesso.')
            return redirect('core:cliente_list')
    else:
        form = ClienteForm()

    return render(request, 'core/cliente_form.html', {'form': form})


@login_required
def cliente_update(request, pk):
    empresa = get_empresa_from_user(request.user)
    cliente = get_object_or_404(Cliente, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente atualizado com sucesso.')
            return redirect('core:cliente_list')
    else:
        form = ClienteForm(instance=cliente)

    return render(request, 'core/cliente_form.html', {'form': form})

# --------- ORÇAMENTOS ---------
@login_required
def orcamento_list(request):
    empresa = get_empresa_from_user(request.user)

    qs = (
        Orcamento.objects
        .filter(empresa=empresa)
        .select_related('cliente')
        .order_by('-data')
    )

    # Filtros
    q = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    data_ini = request.GET.get('data_ini', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    if q:
        # busca em nome do cliente e observações
        qs = qs.filter(
            Q(cliente__nome__icontains=q) |
            Q(observacoes__icontains=q)
        )

        # se for empresa AUTO, também busca em placa
        if empresa.ramo == 'AUTO':
            qs = qs.union(
                Orcamento.objects.filter(
                    empresa=empresa,
                    placa__icontains=q
                )
            )

    if status:
        qs = qs.filter(status=status)

    if data_ini:
        qs = qs.filter(data__date__gte=data_ini)
    if data_fim:
        qs = qs.filter(data__date__lte=data_fim)

    context = {
        'orcamentos': qs,
        'filtro_q': q,
        'filtro_status': status,
        'filtro_data_ini': data_ini,
        'filtro_data_fim': data_fim,
    }
    return render(request, 'core/orcamento_list.html', context)


@login_required
def orcamento_create(request):
    empresa = get_empresa_from_user(request.user)

    if request.method == 'POST':
        form = OrcamentoForm(request.POST, empresa=empresa)
        formset = OrcamentoItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            orcamento = form.save(commit=False)
            orcamento.empresa = empresa   # 👈 seta empresa do usuário
            orcamento.total = Decimal('0')
            orcamento.save()

            total = Decimal('0')
            itens = formset.save(commit=False)

            for item in itens:
                is_vazio = (
                    not item.tipo_item and
                    not item.produto and
                    not item.servico and
                    not item.descricao and
                    not item.quantidade and
                    not item.preco_unitario and
                    not item.total
                )
                if is_vazio:
                    continue

                qtd = item.quantidade or Decimal('0')
                preco = item.preco_unitario or Decimal('0')

                item.orcamento = orcamento
                item.total = qtd * preco
                item.save()

                total += item.total

            orcamento.total = total
            orcamento.save()

            messages.success(request, 'Orçamento criado com sucesso!')
            return redirect('core:orcamento_list')
        else:
            messages.error(request, 'Verifique os campos do orçamento e dos itens.')
    else:
        form = OrcamentoForm(empresa=empresa)
        formset = OrcamentoItemFormSet()

    return render(request, 'core/orcamento_form.html', {
        'form': form,
        'formset': formset,
    })

@login_required
def orcamento_detail(request, pk):
    empresa = get_empresa_from_user(request.user)
    orcamento = get_object_or_404(
        Orcamento.objects.select_related('empresa', 'cliente').prefetch_related('itens'),
        pk=pk,
        empresa=empresa
    )
    return render(request, 'core/orcamento_detail.html', {'orcamento': orcamento})

@login_required
@require_POST
def orcamento_set_status(request, pk):
    empresa = get_empresa_from_user(request.user)
    orcamento = get_object_or_404(Orcamento, pk=pk, empresa=empresa)

    novo_status = request.POST.get('status')

    status_validos = ['RASCUNHO', 'ENVIADO', 'APROVADO', 'RECUSADO']
    if novo_status not in status_validos:
        messages.error(request, 'Status inválido.')
        return redirect('core:orcamento_detail', pk=orcamento.pk)

    orcamento.status = novo_status
    orcamento.save(update_fields=['status'])

    messages.success(
        request,
        f'Status do orçamento alterado para {orcamento.get_status_display()}.'
    )
    return redirect('core:orcamento_detail', pk=orcamento.pk)

@login_required
@require_POST
def orcamento_duplicar(request, pk):
    empresa = get_empresa_from_user(request.user)
    orcamento_original = get_object_or_404(Orcamento, pk=pk, empresa=empresa)

    # Cria uma cópia em RASCUNHO
    novo = Orcamento.objects.create(
        empresa=orcamento_original.empresa,
        cliente=orcamento_original.cliente,
        validade=orcamento_original.validade,
        placa=orcamento_original.placa,
        veiculo_descricao=orcamento_original.veiculo_descricao,
        status='RASCUNHO',
        observacoes=orcamento_original.observacoes,
        total=0
    )

    total = Decimal('0')
    for item in orcamento_original.itens.all():
        novo_item = OrcamentoItem.objects.create(
            orcamento=novo,
            tipo_item=item.tipo_item,
            produto=item.produto,
            servico=item.servico,
            descricao=item.descricao,
            quantidade=item.quantidade,
            preco_unitario=item.preco_unitario,
            total=item.total,
        )
        total += novo_item.total or Decimal('0')

    novo.total = total
    novo.save(update_fields=['total'])

    messages.success(request, f'Orçamento #{orcamento_original.id} duplicado como #{novo.id}.')
    return redirect('core:orcamento_detail', pk=novo.pk)

# ---------- PRODUTOS ----------

@login_required
def produto_list(request):
    empresa = get_empresa_from_user(request.user)
    produtos = Produto.objects.filter(empresa=empresa).order_by('nome')
    return render(request, 'core/produto_list.html', {'produtos': produtos})


@login_required
def produto_create(request):
    empresa = get_empresa_from_user(request.user)

    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            produto = form.save(commit=False)
            produto.empresa = empresa
            produto.save()
            messages.success(request, 'Produto cadastrado com sucesso.')
            return redirect('core:produto_list')
    else:
        form = ProdutoForm()

    return render(request, 'core/produto_form.html', {'form': form})


@login_required
def produto_update(request, pk):
    empresa = get_empresa_from_user(request.user)
    produto = get_object_or_404(Produto, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = ProdutoForm(request.POST, instance=produto)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto atualizado com sucesso.')
            return redirect('core:produto_list')
    else:
        form = ProdutoForm(instance=produto)

    return render(request, 'core/produto_form.html', {'form': form})


# ---------- SERVIÇOS ----------

@login_required
def servico_list(request):
    empresa = get_empresa_from_user(request.user)
    servicos = Servico.objects.filter(empresa=empresa).order_by('nome')
    return render(request, 'core/servico_list.html', {'servicos': servicos})


@login_required
def servico_create(request):
    empresa = get_empresa_from_user(request.user)

    if request.method == 'POST':
        form = ServicoForm(request.POST)
        if form.is_valid():
            servico = form.save(commit=False)
            servico.empresa = empresa
            servico.save()
            messages.success(request, 'Serviço cadastrado com sucesso.')
            return redirect('core:servico_list')
    else:
        form = ServicoForm()

    return render(request, 'core/servico_form.html', {'form': form})


@login_required
def servico_update(request, pk):
    empresa = get_empresa_from_user(request.user)
    servico = get_object_or_404(Servico, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = ServicoForm(request.POST, instance=servico)
        if form.is_valid():
            form.save()
            messages.success(request, 'Serviço atualizado com sucesso.')
            return redirect('core:servico_list')
    else:
        form = ServicoForm(instance=servico)

    return render(request, 'core/servico_form.html', {'form': form})


@login_required
def orcamento_converter(request, pk):
    empresa = get_empresa_from_user(request.user)
    orcamento = get_object_or_404(Orcamento, pk=pk, empresa=empresa)
    if request.method == 'POST':
        tipo = request.POST.get('tipo')  # 'VENDA' ou 'OS'
        if tipo not in ['VENDA', 'OS']:
            messages.error(request, 'Tipo de documento inválido.')
            return redirect('core:orcamento_detail', pk=orcamento.pk)

        # se já existir documento desse orçamento + tipo, reaproveita
        doc_existente = Documento.objects.filter(origem_orcamento=orcamento, tipo=tipo).first()
        if doc_existente:
            messages.info(request, f'{doc_existente.get_tipo_display()} já existente para este orçamento.')
            return redirect('core:documento_detail', pk=doc_existente.pk)

        doc = Documento.objects.create(
            empresa=orcamento.empresa,
            cliente=orcamento.cliente,
            tipo=tipo,
            origem_orcamento=orcamento,
            total=orcamento.total,
            observacoes=orcamento.observacoes,
            placa=orcamento.placa,                         # 👈 novo
            veiculo_descricao=orcamento.veiculo_descricao  # 👈 novo
        )
        messages.success(request, f'{doc.get_tipo_display()} criada a partir do orçamento.')
        return redirect('core:documento_detail', pk=doc.pk)

    # se for GET, volta para detalhe
    return redirect('core:orcamento_detail', pk=orcamento.pk)

@login_required
def documento_list(request):
    empresa = get_empresa_from_user(request.user)

    qs = (
        Documento.objects
        .filter(empresa=empresa)
        .select_related('cliente')
        .order_by('-data')
    )

    q = request.GET.get('q', '').strip()
    tipo = request.GET.get('tipo', '').strip()
    data_ini = request.GET.get('data_ini', '').strip()
    data_fim = request.GET.get('data_fim', '').strip()

    if q:
        qs = qs.filter(
            Q(cliente__nome__icontains=q) |
            Q(observacoes__icontains=q)
        )
        if empresa.ramo == 'AUTO':
            qs = qs.union(
                Documento.objects.filter(
                    empresa=empresa,
                    placa__icontains=q
                )
            )

    if tipo:
        qs = qs.filter(tipo=tipo)

    if data_ini:
        qs = qs.filter(data__date__gte=data_ini)
    if data_fim:
        qs = qs.filter(data__date__lte=data_fim)

    context = {
        'documentos': qs,
        'filtro_q': q,
        'filtro_tipo': tipo,
        'filtro_data_ini': data_ini,
        'filtro_data_fim': data_fim,
    }
    return render(request, 'core/documento_list.html', context)

@login_required
def orcamento_print(request, pk):
    empresa = get_empresa_from_user(request.user)
    orcamento = get_object_or_404(
        Orcamento.objects.select_related('cliente', 'empresa'),
        pk=pk,
        empresa=empresa
    )
    itens = orcamento.itens.all()

    return render(
        request,
        'core/orcamento_print.html',
        {
            'orcamento': orcamento,
            'itens': itens,
        }
    )


@login_required
def documento_detail(request, pk):
    empresa = get_empresa_from_user(request.user)
    documento = get_object_or_404(
        Documento.objects.select_related('empresa', 'cliente', 'origem_orcamento').prefetch_related('pagamentos'),
        pk=pk,
        empresa=empresa
    )
    return render(request, 'core/documento_detail.html', {'documento': documento})


@login_required
def pagamento_create(request, pk):
    empresa = get_empresa_from_user(request.user)
    documento = get_object_or_404(Documento, pk=pk, empresa=empresa)

    if request.method == 'POST':
        form = PagamentoForm(request.POST)
        if form.is_valid():
            pagamento = form.save(commit=False)
            pagamento.documento = documento

            # se valor não informado, assume saldo
            if not pagamento.valor:
                pagamento.valor = documento.saldo

            pagamento.save()
            messages.success(request, 'Pagamento registrado com sucesso.')
            return redirect('core:documento_detail', pk=documento.pk)
    else:
        form = PagamentoForm(initial={'valor': documento.saldo})

    return render(request, 'core/pagamento_form.html', {
        'documento': documento,
        'form': form,
    })

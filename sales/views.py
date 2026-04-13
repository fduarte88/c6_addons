import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from customers.models import Customer
from products.models import Product
from .models import Sale, SaleItem, Payment
from .forms import SaleForm, SaleItemFormSet, PaymentForm


# ──────────────────────────────────────────
# VENTAS — Lista
# ──────────────────────────────────────────

@login_required
def sale_list(request):
    query    = request.GET.get('q', '').strip()
    active_tab = request.GET.get('tab', 'active')  # active | paid | cancelled

    base_qs = Sale.objects.select_related('customer').prefetch_related('items', 'payments')

    if query:
        base_qs = base_qs.filter(
            Q(customer__first_name__icontains=query) |
            Q(customer__last_name__icontains=query)  |
            Q(customer__doc_number__icontains=query)  |
            Q(pk__icontains=query)
        )

    sales_active    = base_qs.filter(status__in=[Sale.STATUS_PENDING, Sale.STATUS_PARTIAL]).order_by('-date', '-pk')
    sales_paid      = base_qs.filter(status=Sale.STATUS_PAID).order_by('-date', '-pk')
    sales_cancelled = base_qs.filter(status=Sale.STATUS_CANCELLED).order_by('-date', '-pk')

    context = {
        'sales_active':    sales_active,
        'sales_paid':      sales_paid,
        'sales_cancelled': sales_cancelled,
        'query':           query,
        'active_tab':      active_tab,
        'total_ventas':    Sale.objects.count(),
        'total_pending':   Sale.objects.filter(status=Sale.STATUS_PENDING).count(),
        'total_partial':   Sale.objects.filter(status=Sale.STATUS_PARTIAL).count(),
        'total_paid':      Sale.objects.filter(status=Sale.STATUS_PAID).count(),
        'total_cancelled': Sale.objects.filter(status=Sale.STATUS_CANCELLED).count(),
    }
    return render(request, 'sales/list.html', context)


# ──────────────────────────────────────────
# VENTAS — Crear
# ──────────────────────────────────────────

@login_required
def sale_create(request):
    # JSON de precios distribuidor para autocompletar en el formulario
    prices = {str(p.pk): float(p.distributor_price)
              for p in Product.objects.filter(is_active=True, quantity__gt=0)}

    if request.method == 'POST':
        form    = SaleForm(request.POST)
        formset = SaleItemFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                sale = form.save()
                formset.instance = sale
                formset.save()
                sale.update_status()
            messages.success(request, f'Venta #{sale.pk} registrada correctamente.')
            return redirect('sale_detail', pk=sale.pk)
    else:
        form    = SaleForm()
        formset = SaleItemFormSet()

    return render(request, 'sales/form.html', {
        'form':      form,
        'formset':   formset,
        'action':    'Nueva',
        'prices_json': json.dumps(prices),
    })


# ──────────────────────────────────────────
# VENTAS — Detalle
# ──────────────────────────────────────────

@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('customer')
                    .prefetch_related('items__product', 'payments'),
        pk=pk
    )
    payment_form = PaymentForm(sale=sale, initial={'date': sale.date})
    return render(request, 'sales/detail.html', {
        'sale':         sale,
        'payment_form': payment_form,
    })


# ──────────────────────────────────────────
# VENTAS — Cancelar
# ──────────────────────────────────────────

@login_required
def sale_cancel(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    if request.method == 'POST':
        if sale.status != Sale.STATUS_CANCELLED:
            # Devuelve stock de cada ítem
            for item in sale.items.select_related('product').all():
                item.product.quantity += item.quantity
                item.product.save(update_fields=['quantity'])
        sale.status = Sale.STATUS_CANCELLED
        sale.save(update_fields=['status'])
        messages.success(request, f'Venta #{sale.pk} cancelada.')
        return redirect('sale_list')
    return render(request, 'sales/confirm_cancel.html', {'sale': sale})


# ──────────────────────────────────────────
# PAGOS — Agregar pago a una venta
# ──────────────────────────────────────────

@login_required
def payment_add(request, sale_pk):
    sale = get_object_or_404(Sale, pk=sale_pk)

    if sale.status == Sale.STATUS_PAID:
        messages.error(request, 'Esta venta ya está totalmente pagada.')
        return redirect('sale_detail', pk=sale.pk)

    if sale.status == Sale.STATUS_CANCELLED:
        messages.error(request, 'No se pueden registrar pagos en una venta cancelada.')
        return redirect('sale_detail', pk=sale.pk)

    if request.method == 'POST':
        form = PaymentForm(sale=sale, data=request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.sale = sale
            payment.save()  # sale.update_status() se llama en Payment.save()
            messages.success(
                request,
                f'Pago de Gs. {payment.amount:,.0f} registrado. '
                f'Saldo restante: Gs. {sale.balance:,.0f}.'
            )
            return redirect('sale_detail', pk=sale.pk)
    else:
        form = PaymentForm(sale=sale)

    return render(request, 'sales/payment_form.html', {'form': form, 'sale': sale})


# ──────────────────────────────────────────
# PAGOS — Eliminar pago
# ──────────────────────────────────────────

@login_required
def payment_delete(request, pk):
    payment = get_object_or_404(Payment, pk=pk)
    sale    = payment.sale
    if request.method == 'POST':
        payment.delete()
        sale.update_status()
        messages.success(request, 'Pago eliminado.')
        return redirect('sale_detail', pk=sale.pk)
    return render(request, 'sales/payment_confirm_delete.html', {'payment': payment})


# ──────────────────────────────────────────
# ESTADO DE CUENTA — por cliente
# ──────────────────────────────────────────

@login_required
def customer_statement(request, customer_pk):
    customer = get_object_or_404(Customer, pk=customer_pk)
    sales    = Sale.objects.filter(customer=customer) \
                           .prefetch_related('items__product', 'payments') \
                           .order_by('-date', '-created_at')

    # Totales globales del cliente
    total_ventas  = sum(s.total       for s in sales)
    total_pagado  = sum(s.total_paid  for s in sales)
    total_saldo   = sum(s.balance     for s in sales
                        if s.status != Sale.STATUS_CANCELLED)

    context = {
        'customer':     customer,
        'sales':        sales,
        'total_ventas': total_ventas,
        'total_pagado': total_pagado,
        'total_saldo':  total_saldo,
    }
    return render(request, 'sales/statement.html', context)


# ──────────────────────────────────────────
# API — Búsqueda de clientes (AJAX)
# ──────────────────────────────────────────

@login_required
def customer_lookup_api(request, pk):
    """Devuelve datos de un cliente por su ID (código)."""
    try:
        c = Customer.objects.get(pk=pk, is_active=True)
        return JsonResponse({
            'id':       c.pk,
            'code':     c.pk,
            'name':     c.full_name,
            'doc':      c.doc_number,
            'phone':    c.phone_display,
        })
    except Customer.DoesNotExist:
        return JsonResponse({'error': 'Cliente no encontrado'}, status=404)


@login_required
def customer_search_api(request):
    """Busca clientes activos por nombre, apellido o documento."""
    q = request.GET.get('q', '').strip()
    if not q:
        return JsonResponse({'results': []})
    customers = Customer.objects.filter(
        is_active=True
    ).filter(
        Q(first_name__icontains=q) |
        Q(last_name__icontains=q)  |
        Q(doc_number__icontains=q) |
        Q(pk__icontains=q)
    ).order_by('last_name', 'first_name')[:20]
    results = [
        {'id': c.pk, 'code': c.pk, 'name': c.full_name, 'doc': c.doc_number}
        for c in customers
    ]
    return JsonResponse({'results': results})

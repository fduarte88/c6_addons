from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from products.models import Product
from .models import Purchase, PurchaseItem
from .forms import PurchaseForm, PurchaseItemFormSet


@login_required
def purchase_list(request):
    query = request.GET.get('q', '').strip()
    purchases = Purchase.objects.prefetch_related('items__product')

    if query:
        purchases = purchases.filter(
            Q(supplier__name__icontains=query) |
            Q(pk__icontains=query)
        )

    purchases_list  = list(purchases)
    tab_total       = sum(p.total for p in purchases_list)

    context = {
        'purchases':     purchases_list,
        'query':         query,
        'total_compras': Purchase.objects.count(),
        'tab_total':     tab_total,
    }
    return render(request, 'purchases/list.html', context)


@login_required
def purchase_create(request):
    if request.method == 'POST':
        form    = PurchaseForm(request.POST)
        formset = PurchaseItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                purchase = form.save()
                formset.instance = purchase
                formset.save()
            messages.success(request, f'Compra #{purchase.pk} registrada. Stock actualizado.')
            return redirect('purchase_list')
    else:
        form    = PurchaseForm()
        formset = PurchaseItemFormSet()

    context = {
        'form':    form,
        'formset': formset,
        'action':  'Registrar',
    }
    return render(request, 'purchases/form.html', context)


# ──────────────────────────────────────────
# API — Búsqueda de productos (AJAX, para el formulario de compras)
# ──────────────────────────────────────────

@login_required
def purchase_product_lookup_api(request, pk):
    """Devuelve datos de un producto por su ID (código)."""
    try:
        p = Product.objects.get(pk=pk, is_active=True)
        return JsonResponse({
            'id':          p.pk,
            'code':        p.pk,
            'description': p.description,
            'cost':        float(p.cost),
        })
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Producto no encontrado'}, status=404)


@login_required
def purchase_product_search_api(request):
    """Busca productos activos por descripción o código. q='*' devuelve todos."""
    q = request.GET.get('q', '').strip()
    base_qs = Product.objects.filter(is_active=True).order_by('description')
    if not q or q == '*':
        products = base_qs[:50]
    else:
        products = base_qs.filter(
            Q(description__icontains=q) | Q(pk__icontains=q)
        )[:20]
    results = [
        {'id': p.pk, 'code': p.pk, 'description': p.description, 'cost': float(p.cost)}
        for p in products
    ]
    return JsonResponse({'results': results})


@login_required
def purchase_detail(request, pk):
    purchase = get_object_or_404(Purchase.objects.prefetch_related('items__product'), pk=pk)
    return render(request, 'purchases/detail.html', {'purchase': purchase})


@login_required
def purchase_delete(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)
    if request.method == 'POST':
        # Al eliminar la compra, los PurchaseItem.delete() devuelven el stock
        for item in purchase.items.all():
            item.delete()
        purchase.delete()
        messages.success(request, f'Compra #{pk} eliminada. Stock revertido.')
        return redirect('purchase_list')
    return render(request, 'purchases/confirm_delete.html', {'purchase': purchase})

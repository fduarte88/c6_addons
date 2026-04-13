import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from products.models import Product
from .models import Purchase, PurchaseItem
from .forms import PurchaseForm, PurchaseItemFormSet


@login_required
def purchase_list(request):
    query = request.GET.get('q', '').strip()
    purchases = Purchase.objects.prefetch_related('items__product')

    if query:
        purchases = purchases.filter(
            Q(supplier__icontains=query) |
            Q(pk__icontains=query)
        )

    context = {
        'purchases':      purchases,
        'query':          query,
        'total_compras':  Purchase.objects.count(),
    }
    return render(request, 'purchases/list.html', context)


@login_required
def purchase_create(request):
    prices = {str(p.pk): float(p.cost) for p in Product.objects.filter(is_active=True)}

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
        'prices':  json.dumps(prices),
    }
    return render(request, 'purchases/form.html', context)


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

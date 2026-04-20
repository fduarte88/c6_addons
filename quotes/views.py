import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from suppliers.models import Supplier
from .models import SupplierQuoteConfig, Quote


@login_required
def quote_calculator(request):
    suppliers = Supplier.objects.filter(is_active=True).order_by('name')
    quotes    = Quote.objects.select_related('supplier').order_by('-created_at')[:20]
    return render(request, 'quotes/calculator.html', {
        'suppliers': suppliers,
        'quotes':    quotes,
    })


@login_required
def supplier_config_api(request, supplier_pk):
    """Devuelve la config de campos del presupuesto para un proveedor."""
    try:
        config = SupplierQuoteConfig.objects.get(supplier_id=supplier_pk)
        return JsonResponse({'fields': config.fields_config})
    except SupplierQuoteConfig.DoesNotExist:
        return JsonResponse({'fields': []})


@login_required
def quote_save(request):
    if request.method != 'POST':
        return redirect('quote_calculator')

    supplier_pk = request.POST.get('supplier')
    cotizacion  = request.POST.get('cotizacion', '0').replace(',', '.')
    total_usd   = request.POST.get('total_usd', '0').replace(',', '.')
    total_gs    = request.POST.get('total_gs', '0').replace(',', '.').replace('.', '', -1)
    notes       = request.POST.get('notes', '')
    fields_json = request.POST.get('fields_data', '{}')

    try:
        supplier = Supplier.objects.get(pk=supplier_pk)
    except Supplier.DoesNotExist:
        messages.error(request, 'Proveedor no encontrado.')
        return redirect('quote_calculator')

    try:
        fields_data = json.loads(fields_json)
    except (json.JSONDecodeError, ValueError):
        fields_data = {}

    Quote.objects.create(
        supplier=supplier,
        cotizacion=float(cotizacion),
        fields_data=fields_data,
        total_usd=float(total_usd),
        total_gs=float(total_gs.replace('.', '').replace(',', '.')) if total_gs else 0,
        notes=notes,
    )
    messages.success(request, 'Presupuesto guardado correctamente.')
    return redirect('quote_calculator')


@login_required
def quote_delete(request, pk):
    quote = get_object_or_404(Quote, pk=pk)
    if request.method == 'POST':
        quote.delete()
        messages.success(request, 'Presupuesto eliminado.')
    return redirect('quote_calculator')

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Supplier
from .forms import SupplierForm


@login_required
def supplier_list(request):
    query    = request.GET.get('q', '').strip()
    status   = request.GET.get('status', '')
    suppliers = Supplier.objects.all()

    if query:
        suppliers = suppliers.filter(
            Q(name__icontains=query) |
            Q(doc_number__icontains=query) |
            Q(contact__icontains=query)
        )
    if status == 'active':
        suppliers = suppliers.filter(is_active=True)
    elif status == 'inactive':
        suppliers = suppliers.filter(is_active=False)

    context = {
        'suppliers': suppliers,
        'query':     query,
        'status':    status,
        'total':     Supplier.objects.count(),
        'activos':   Supplier.objects.filter(is_active=True).count(),
        'inactivos': Supplier.objects.filter(is_active=False).count(),
    }
    return render(request, 'suppliers/list.html', context)


@login_required
def supplier_create(request):
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.is_active = True
            supplier.save()
            messages.success(request, f'Proveedor "{supplier.name}" registrado.')
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'suppliers/form.html', {'form': form, 'action': 'Registrar'})


@login_required
def supplier_edit(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, f'Proveedor "{supplier.name}" actualizado.')
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'suppliers/form.html', {'form': form, 'action': 'Editar', 'supplier': supplier})


@login_required
def supplier_delete(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        name = supplier.name
        supplier.delete()
        messages.success(request, f'Proveedor "{name}" eliminado.')
        return redirect('supplier_list')
    return render(request, 'suppliers/confirm_delete.html', {'supplier': supplier})

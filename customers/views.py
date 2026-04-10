from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Customer
from .forms import CustomerForm


@login_required
def customer_list(request):
    query  = request.GET.get('q', '').strip()
    status = request.GET.get('status', '')

    customers = Customer.objects.all()

    if query:
        customers = customers.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)  |
            Q(doc_number__icontains=query) |
            Q(email__icontains=query)      |
            Q(city__icontains=query)
        )

    if status == 'active':
        customers = customers.filter(is_active=True)
    elif status == 'inactive':
        customers = customers.filter(is_active=False)

    context = {
        'customers': customers,
        'query':     query,
        'status':    status,
        'total':     Customer.objects.count(),
        'activos':   Customer.objects.filter(is_active=True).count(),
        'inactivos': Customer.objects.filter(is_active=False).count(),
    }
    return render(request, 'customers/list.html', context)


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    return render(request, 'customers/detail.html', {'customer': customer})


@login_required
def customer_create(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.is_active = True   # siempre activo al crear
            customer.save()
            messages.success(request, f'Cliente "{customer.full_name}" registrado correctamente.')
            return redirect('customer_list')
    else:
        form = CustomerForm()

    return render(request, 'customers/form.html', {'form': form, 'action': 'Registrar'})


@login_required
def customer_edit(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            messages.success(request, f'Cliente "{customer.full_name}" actualizado correctamente.')
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)

    return render(request, 'customers/form.html', {
        'form':     form,
        'action':   'Editar',
        'customer': customer,
    })


@login_required
def customer_delete(request, pk):
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == 'POST':
        name = customer.full_name
        customer.delete()
        messages.success(request, f'Cliente "{name}" eliminado correctamente.')
        return redirect('customer_list')

    return render(request, 'customers/confirm_delete.html', {'customer': customer})

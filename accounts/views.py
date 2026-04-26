from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from .forms import UserCreateForm, UserEditForm
from customers.models import Customer
from products.models import Product
from sales.models import Sale
from purchases.models import Purchase


# ──────────────────────────────────────────
# Decorador: solo administradores
# ──────────────────────────────────────────
def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
            messages.error(request, 'No tienes permisos para acceder a esta sección.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ──────────────────────────────────────────
# Autenticación
# ──────────────────────────────────────────
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, 'Usuario o contraseña incorrectos.')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ──────────────────────────────────────────
# Dashboard
# ──────────────────────────────────────────
@login_required
def dashboard_view(request):
    context = {
        'total_customers': Customer.objects.count(),
        'total_products':  Product.objects.filter(is_active=True).count(),
        'total_sales':     Sale.objects.exclude(status=Sale.STATUS_CANCELLED).count(),
        'total_purchases': Purchase.objects.count(),
    }
    return render(request, 'dashboard.html', context)


# ──────────────────────────────────────────
# Gestión de usuarios (solo admin)
# ──────────────────────────────────────────
@login_required
@admin_required
def user_list(request):
    query = request.GET.get('q', '').strip()
    role  = request.GET.get('role', '')
    users = User.objects.select_related('profile').order_by('username')

    if query:
        users = users.filter(username__icontains=query) \
                   | users.filter(first_name__icontains=query) \
                   | users.filter(last_name__icontains=query) \
                   | users.filter(email__icontains=query)

    if role in (UserProfile.ADMIN, UserProfile.OPERATOR):
        users = users.filter(profile__role=role)

    context = {
        'users':      users,
        'query':      query,
        'role_filter': role,
        'roles':      UserProfile.ROLE_CHOICES,
    }
    return render(request, 'accounts/users/list.html', context)


@login_required
@admin_required
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Usuario "{user.username}" creado correctamente.')
            return redirect('user_list')
    else:
        form = UserCreateForm()

    return render(request, 'accounts/users/form.html', {'form': form, 'action': 'Crear'})


@login_required
@admin_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Usuario "{user.username}" actualizado correctamente.')
            return redirect('user_list')
    else:
        form = UserEditForm(instance=user)

    return render(request, 'accounts/users/form.html', {
        'form':   form,
        'action': 'Editar',
        'edit_user': user,
    })


@login_required
@admin_required
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)

    if user == request.user:
        messages.error(request, 'No puedes eliminar tu propio usuario.')
        return redirect('user_list')

    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Usuario "{username}" eliminado correctamente.')
        return redirect('user_list')

    return render(request, 'accounts/users/confirm_delete.html', {'edit_user': user})

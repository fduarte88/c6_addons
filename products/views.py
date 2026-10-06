import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Category, Origin, Product
from .forms import CategoryForm, OriginForm, ProductForm
from accounts.views import admin_required


# ──────────────────────────────────────────
# CATEGORÍAS
# ──────────────────────────────────────────

@login_required
@admin_required
def category_list(request):
    categories = Category.objects.tree()
    return render(request, 'products/categories/list.html', {'categories': categories})


@login_required
@admin_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f'Categoría "{cat.name}" creada correctamente.')
            return redirect('category_list')
    else:
        form = CategoryForm()
    return render(request, 'products/categories/form.html', {'form': form, 'action': 'Crear'})


@login_required
@admin_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Categoría "{category.name}" actualizada.')
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'products/categories/form.html', {
        'form': form, 'action': 'Editar', 'category': category,
    })


@login_required
@admin_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        if category.products.exists():
            messages.error(request, f'No se puede eliminar "{category.name}": tiene productos asociados.')
            return redirect('category_list')
        if category.children.exists():
            messages.error(request, f'No se puede eliminar "{category.name}": tiene subcategorías.')
            return redirect('category_list')
        name = category.name
        category.delete()
        messages.success(request, f'Categoría "{name}" eliminada.')
        return redirect('category_list')
    return render(request, 'products/categories/confirm_delete.html', {'category': category})


# ──────────────────────────────────────────
# PRODUCTOS
# ──────────────────────────────────────────

@login_required
def product_list(request):
    query    = request.GET.get('q', '').strip()
    cat_id   = request.GET.get('category', '')
    status   = request.GET.get('status', '')

    products = Product.objects.select_related('category__parent').all()

    if query:
        products = products.filter(
            Q(description__icontains=query) |
            Q(origin__name__icontains=query) |
            Q(category__name__icontains=query)
        )
    if cat_id:
        # Una categoría principal incluye los productos de sus subcategorías
        products = products.filter(Q(category_id=cat_id) | Q(category__parent_id=cat_id))
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)

    context = {
        'products':   products,
        'query':      query,
        'cat_id':     cat_id,
        'status':     status,
        'categories': Category.objects.filter(is_active=True).tree(),
        'total':      Product.objects.count(),
        'activos':    Product.objects.filter(is_active=True).count(),
        'sin_stock':  Product.objects.filter(quantity=0).count(),
    }
    return render(request, 'products/list.html', context)


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category__parent'), pk=pk)
    return render(request, 'products/detail.html', {'product': product})


def _category_types_json():
    """Devuelve JSON con {id: tipo} para usar en el JS del formulario."""
    data = {str(c.pk): c.tipo for c in Category.objects.filter(is_active=True)}
    return json.dumps(data)


@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.is_active = True    # siempre activo al crear
            product.save()
            form.save_m2m()             # guarda los talles (ProductSize)
            messages.success(request, f'Producto "{product.description}" registrado correctamente.')
            return redirect('product_list')
    else:
        form = ProductForm()

    return render(request, 'products/form.html', {
        'form':           form,
        'action':         'Registrar',
        'category_types': _category_types_json(),
    })


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Producto "{product.description}" actualizado.')
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)

    return render(request, 'products/form.html', {
        'form':           form,
        'action':         'Editar',
        'product':        product,
        'category_types': _category_types_json(),
    })


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    # Los ítems de venta y de compra protegen al producto (PROTECT)
    in_use  = product.saleitem_set.exists() or product.purchaseitem_set.exists()
    if request.method == 'POST':
        if in_use:
            messages.error(request, f'No se puede eliminar "{product.description}": tiene ventas o compras registradas. '
                                    'Puedes desactivarlo desde Editar.')
            return redirect('product_list')
        name = product.description
        product.delete()
        messages.success(request, f'Producto "{name}" eliminado.')
        return redirect('product_list')
    return render(request, 'products/confirm_delete.html', {'product': product, 'in_use': in_use})


# ──────────────────────────────────────────
# PROCEDENCIAS (Origin)
# ──────────────────────────────────────────

@login_required
@admin_required
def origin_list(request):
    origins = Origin.objects.all()
    return render(request, 'products/origins/list.html', {'origins': origins})


@login_required
@admin_required
def origin_create(request):
    form = OriginForm(request.POST or None)
    if form.is_valid():
        origin = form.save()
        messages.success(request, f'Procedencia "{origin.name}" creada.')
        return redirect('origin_list')
    return render(request, 'products/origins/form.html', {'form': form, 'action': 'Nueva'})


@login_required
@admin_required
def origin_edit(request, pk):
    origin = get_object_or_404(Origin, pk=pk)
    form   = OriginForm(request.POST or None, instance=origin)
    if form.is_valid():
        form.save()
        messages.success(request, f'Procedencia "{origin.name}" actualizada.')
        return redirect('origin_list')
    return render(request, 'products/origins/form.html', {'form': form, 'action': 'Editar', 'origin': origin})


@login_required
@admin_required
def origin_delete(request, pk):
    origin = get_object_or_404(Origin, pk=pk)
    if request.method == 'POST':
        if origin.products.exists():
            messages.error(request, f'No se puede eliminar "{origin.name}": tiene productos asociados.')
            return redirect('origin_list')
        name = origin.name
        origin.delete()
        messages.success(request, f'Procedencia "{name}" eliminada.')
        return redirect('origin_list')
    return render(request, 'products/origins/confirm_delete.html', {'origin': origin})

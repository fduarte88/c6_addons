from urllib.parse import quote, urlencode

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from products.models import Category, Product
from products.templatetags.guarani import gs


# (valor en la URL, etiqueta, orden)
SORT_OPTIONS = [
    ('recientes',   'Más recientes',            ('-created_at', '-pk')),
    ('precio-asc',  'Precio: más bajo primero', ('list_price', 'pk')),
    ('precio-desc', 'Precio: más alto primero', ('-list_price', '-pk')),
]
PER_PAGE = 24  # múltiplo de 3 y de 2: filas completas en escritorio y tablet


def whatsapp_url(request, product, talle=''):
    """Link wa.me al WhatsApp de la tienda con el pedido ya escrito (incluye el talle elegido)."""
    detail = product.description
    if talle:
        detail += f' (Talle {talle})'
    elif product.size_display != '—':
        detail += f' ({product.size_display})'
    lines = [
        '¡Hola c6 Store! Quiero comprar:',
        detail,
        f'Precio: {gs(product.list_price)}',
        f'Código: {product.pk}',   # el mismo código que se usa para buscarlo en Ventas
    ]
    if product.image:
        lines.append(f'Foto: {request.build_absolute_uri(product.image.url)}')
    text = '\n'.join(lines)
    return f'https://wa.me/{settings.STORE_WHATSAPP}?text={quote(text)}'


# ──────────────────────────────────────────
# TIENDA — Página de categoría (ej: /tienda/camisetas/?sub=polo)
# ──────────────────────────────────────────

def category(request, slug):
    category = get_object_or_404(Category.objects.select_related('parent'), slug=slug, is_active=True)

    # Una subcategoría se muestra como pestaña dentro de la página de su categoría padre
    if category.parent_id:
        url = reverse('store_category', args=[category.parent.slug])
        return redirect(f'{url}?{urlencode({"sub": category.slug})}')

    subcategories = list(category.children.filter(is_active=True).order_by('pk'))

    # Solo productos a la venta: activos y con stock
    all_products = Product.objects.filter(is_active=True, quantity__gt=0).filter(
        Q(category=category) | Q(category__in=subcategories)
    )
    counts = dict(all_products.order_by().values_list('category_id').annotate(n=Count('pk')))

    sub     = request.GET.get('sub', '')
    current = next((s for s in subcategories if s.slug == sub), None)

    sort     = request.GET.get('orden', '')
    ordering = {key: order for key, _, order in SORT_OPTIONS}
    if sort not in ordering:
        sort = SORT_OPTIONS[0][0]

    def query_for(sub_slug):
        """Query string con la subcategoría y el orden (el orden por defecto no se escribe)."""
        params = {'sub': sub_slug, 'orden': '' if sort == SORT_OPTIONS[0][0] else sort}
        return urlencode({k: v for k, v in params.items() if v})

    tabs = [{'label': 'Todos', 'query': query_for(''), 'count': sum(counts.values()), 'active': current is None}]
    tabs += [
        {'label': s.name, 'query': query_for(s.slug), 'count': counts.get(s.pk, 0), 'active': s == current}
        for s in subcategories
    ]

    products = all_products.filter(category=current) if current else all_products
    products = products.select_related('category', 'origin').prefetch_related('sizes').order_by(*ordering[sort])
    page     = Paginator(products, PER_PAGE).get_page(request.GET.get('page'))

    return render(request, 'store/category.html', {
        'category':     category,
        'current':      current,
        'tabs':         tabs,
        'page':         page,
        'sort':         sort,
        'sort_options': [(key, label) for key, label, _ in SORT_OPTIONS],
        'query':        query_for(current.slug if current else ''),  # para la paginación
        'whatsapp':     bool(settings.STORE_WHATSAPP),
    })


# ──────────────────────────────────────────
# TIENDA — Pedido por WhatsApp (ej: /tienda/pedido/27/?talle=M)
# ──────────────────────────────────────────

def whatsapp_order(request, pk):
    """Valida el talle elegido y redirige al chat de WhatsApp con el pedido escrito."""
    if not settings.STORE_WHATSAPP:
        raise Http404
    product = get_object_or_404(
        Product.objects.select_related('category__parent'), pk=pk, is_active=True, quantity__gt=0
    )
    talle = request.GET.get('talle', '')
    # Si el producto tiene talles, elegir uno con stock es obligatorio
    if product.talles and not product.sizes.filter(talle=talle, quantity__gt=0).exists():
        shop = product.category.parent or product.category
        return redirect('store_category', slug=shop.slug)
    return redirect(whatsapp_url(request, product, talle if product.talles else ''))

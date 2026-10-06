from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from accounts.views import dashboard_view

urlpatterns = [
    path('', TemplateView.as_view(template_name='landing.html'), name='home'),
    path('tienda/', include('store.urls')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('clientes/', include('customers.urls')),
    path('productos/', include('products.urls')),
    path('ventas/', include('sales.urls')),
    path('compras/', include('purchases.urls')),
    path('proveedores/', include('suppliers.urls')),
    path('presupuestos/', include('quotes.urls')),
    path('accounts/', include('accounts.urls')),
]

# En desarrollo Django sirve las imágenes subidas; en producción lo hace el servidor web
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

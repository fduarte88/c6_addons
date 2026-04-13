from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from accounts.views import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('clientes/', include('customers.urls')),
    path('productos/', include('products.urls')),
    path('ventas/', include('sales.urls')),
    path('compras/', include('purchases.urls')),
    path('proveedores/', include('suppliers.urls')),
    path('accounts/', include('accounts.urls')),
    path('', RedirectView.as_view(url='/accounts/login/', permanent=False)),
]

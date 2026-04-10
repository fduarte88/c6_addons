from django.contrib import admin
from django.urls import path, include
from accounts.views import dashboard_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('clientes/', include('customers.urls')),
    path('', include('accounts.urls')),
]

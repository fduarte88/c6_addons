from django.urls import path
from . import views

urlpatterns = [
    path('pedido/<int:pk>/', views.whatsapp_order, name='store_whatsapp_order'),
    path('<slug:slug>/', views.category, name='store_category'),
]

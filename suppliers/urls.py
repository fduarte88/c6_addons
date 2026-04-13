from django.urls import path
from . import views

urlpatterns = [
    path('',                  views.supplier_list,   name='supplier_list'),
    path('nuevo/',            views.supplier_create, name='supplier_create'),
    path('<int:pk>/editar/',  views.supplier_edit,   name='supplier_edit'),
    path('<int:pk>/eliminar/', views.supplier_delete, name='supplier_delete'),
]

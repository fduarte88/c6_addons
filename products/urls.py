from django.urls import path
from . import views

urlpatterns = [
    # Productos
    path('',                           views.product_list,    name='product_list'),
    path('nuevo/',                     views.product_create,  name='product_create'),
    path('<int:pk>/',                  views.product_detail,  name='product_detail'),
    path('<int:pk>/editar/',           views.product_edit,    name='product_edit'),
    path('<int:pk>/eliminar/',         views.product_delete,  name='product_delete'),

    # Categorías
    path('categorias/',                views.category_list,   name='category_list'),
    path('categorias/nueva/',          views.category_create, name='category_create'),
    path('categorias/<int:pk>/editar/', views.category_edit,  name='category_edit'),
    path('categorias/<int:pk>/eliminar/', views.category_delete, name='category_delete'),
]

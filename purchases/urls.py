from django.urls import path
from . import views

urlpatterns = [
    path('',              views.purchase_list,   name='purchase_list'),
    path('nueva/',        views.purchase_create, name='purchase_create'),
    path('<int:pk>/',     views.purchase_detail, name='purchase_detail'),
    path('<int:pk>/eliminar/', views.purchase_delete, name='purchase_delete'),
]

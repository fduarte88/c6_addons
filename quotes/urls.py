from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.quote_calculator,    name='quote_calculator'),
    path('guardar/',                      views.quote_save,          name='quote_save'),
    path('<int:pk>/eliminar/',            views.quote_delete,        name='quote_delete'),
    path('api/config/<int:supplier_pk>/', views.supplier_config_api, name='supplier_config_api'),
]

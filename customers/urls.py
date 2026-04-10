from django.urls import path
from . import views

urlpatterns = [
    path('',                        views.customer_list,   name='customer_list'),
    path('nuevo/',                  views.customer_create, name='customer_create'),
    path('<int:pk>/',               views.customer_detail, name='customer_detail'),
    path('<int:pk>/editar/',        views.customer_edit,   name='customer_edit'),
    path('<int:pk>/eliminar/',      views.customer_delete, name='customer_delete'),
]

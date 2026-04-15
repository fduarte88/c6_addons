from django.urls import path
from . import views

urlpatterns = [
    # Ventas
    path('',                           views.sale_list,          name='sale_list'),
    path('nueva/',                     views.sale_create,        name='sale_create'),
    path('<int:pk>/',                  views.sale_detail,        name='sale_detail'),
    path('<int:pk>/cancelar/',         views.sale_cancel,        name='sale_cancel'),

    # Pagos
    path('<int:sale_pk>/pago/',        views.payment_add,        name='payment_add'),
    path('pago/<int:pk>/eliminar/',    views.payment_delete,     name='payment_delete'),

    # Estado de cuenta
    path('cliente/<int:customer_pk>/estado-cuenta/',     views.customer_statement,     name='customer_statement'),
    path('cliente/<int:customer_pk>/estado-cuenta/pdf/', views.customer_statement_pdf, name='customer_statement_pdf'),

    # API búsqueda de cliente
    path('api/cliente/',      views.customer_search_api, name='customer_search_api'),
    path('api/cliente/<int:pk>/', views.customer_lookup_api, name='customer_lookup_api'),
]

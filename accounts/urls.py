from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Gestión de usuarios
    path('usuarios/',               views.user_list,   name='user_list'),
    path('usuarios/nuevo/',         views.user_create, name='user_create'),
    path('usuarios/<int:pk>/editar/', views.user_edit, name='user_edit'),
    path('usuarios/<int:pk>/eliminar/', views.user_delete, name='user_delete'),
]

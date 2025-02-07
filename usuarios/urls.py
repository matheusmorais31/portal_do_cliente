    # urls.py

from django.urls import path
from .views import ProfileView, CustomLogoutView
from . import views  

app_name = 'usuarios'

urlpatterns = [
    path('registrar/', views.registrar_usuario, name='registrar'),
    path('login/', views.login_usuario, name='login_usuario'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('lista_usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('editar/<int:usuario_id>/', views.editar_usuario, name='editar_usuario'),
    path('buscar_usuarios/', views.buscar_usuarios_ad, name='buscar_usuarios_ad'),
    path('importar_usuarios/', views.importar_usuarios_ad, name='importar_usuarios_ad'),
    path('grupos/', views.lista_grupos, name='lista_grupos'),
    path('grupos/cadastrar_grupo/', views.cadastrar_grupo, name='cadastrar_grupo'),
    path('grupos/buscar_participantes/', views.buscar_participantes, name='buscar_participantes'),
    path('grupos/editar_grupo/<int:grupo_id>/', views.editar_grupo, name='editar_grupo'),
    path('grupos/excluir_grupo/<int:grupo_id>/', views.excluir_grupo, name='excluir_grupo'),
    path('liberar_permissoes/', views.liberar_permissoes, name='liberar_permissoes'),   
    path('sugestoes/', views.sugestoes, name='sugestoes'),
    path('perfil/', ProfileView.as_view(), name='perfil_usuario'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('duplicar_acesso/', views.duplicar_acesso, name='duplicar_acesso'),
    path('buscar_entidade/', views.buscar_entidade, name='buscar_entidade'),
]

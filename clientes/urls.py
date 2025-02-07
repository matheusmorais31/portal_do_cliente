from django.urls import path
from . import views

app_name = 'clientes'

urlpatterns = [
    path('listar/', views.listar_clientes_view, name='listar_clientes'),
    path('importar/', views.listar_clientes_disponiveis_view, name='importar_clientes'),
    path('buscar-clientes/', views.buscar_clientes, name='buscar_clientes'),
    path('editar-senha/<int:cliente_id>/', views.editar_cliente_senha, name='editar_senha'),
    path('meus-pedidos/', views.meus_pedidos_view, name='meus_pedidos'),
    path('pedidos-meus-clientes/', views.pedidos_meus_clientes_view, name='pedidos_meus_clientes'),
 
   path('clientes/visualizar-danfe-html/<slug:nf_numero>/', views.visualizar_danfe_html, name='visualizar_danfe_html')






]

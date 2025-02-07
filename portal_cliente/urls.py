# portal_cliente/urls.py

from django.contrib import admin
from django.urls import path, include
from portal_cliente.views import home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('clientes/', include('clientes.urls')),
    path('accounts/', include('django.contrib.auth.urls')),  # URLs de autenticação do Django
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),  

]

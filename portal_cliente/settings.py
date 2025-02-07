from pathlib import Path
from decouple import config, Csv
import os
import logging.config

BASE_DIR = Path(__file__).resolve().parent.parent

# Diretório para logs
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)  # Cria o diretório 'logs' se não existir

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['172.16.41.34', '127.0.0.1', '10.81.234.2']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'portal_cliente',
    'clientes',
    'usuarios',
    'django.contrib.humanize',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'usuarios.session_timeout_middleware.SessionIdleTimeoutMiddleware',
    'usuarios.middleware.LoginRequiredMiddleware',



]



ROOT_URLCONF = 'portal_cliente.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Você pode adicionar outros diretórios de template aqui, se precisar
        'DIRS': [BASE_DIR / 'portal_cliente' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',  # Necessário para autenticação
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'portal_cliente.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', default='3306'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
# Pasta "static" no mesmo nível que "manage.py"
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# Pasta final para coletar estáticos em produção
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Configuração de mensagens
from django.contrib.messages import constants as messages

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# Configuração de autenticação
LOGIN_URL = '/usuarios/login/'
LOGIN_REDIRECT_URL = '/'  
LOGOUT_REDIRECT_URL = '/'

# Configuração de logs
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'debug.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],  
            'level': 'DEBUG',
            'propagate': True,
        },
        'clientes': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Authentication backends
# Authentication backends
AUTHENTICATION_BACKENDS = [
    'usuarios.auth_backends.ActiveDirectoryBackend',
    'django.contrib.auth.backends.ModelBackend',
    'usuarios.authentication.CustomBackend',
]
LDAP_SERVER = config('LDAP_SERVER')
LDAP_USER = config('LDAP_USER')
LDAP_PASSWORD = config('LDAP_PASSWORD')
LDAP_SEARCH_BASE = config('LDAP_SEARCH_BASE')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'usuarios.Usuario'
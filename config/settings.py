"""
Django settings for Hiver project.

Interactive legal timelines, document archiving, and AI-assisted research.
"""

import platform
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-key-change-in-production')

DEBUG = os.getenv('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apps.core',
    'apps.accounts',
    'apps.timeline',
    'apps.archive',
    'apps.ai_assistant',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.RustDIDAuthenticationMiddleware',
    'apps.core.middleware.CaseSelectionMiddleware',
    'apps.core.middleware.SessionSecurityMiddleware',
]

ROOT_URLCONF = 'config.urls'

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/timeline/'
LOGOUT_REDIRECT_URL = '/timeline/'

RUST_DID_LIB_EXTENSION = {
    'Linux': 'so',
    'Darwin': 'dylib',
    'Windows': 'dll'
}.get(platform.system(), 'so')

RUST_DID_LIB_PATH = os.getenv('RUST_DID_LIB_PATH',
    BASE_DIR / 'rust_did' / 'target' / 'release' / f'libdid_rust.{RUST_DID_LIB_EXTENSION}'
)

DID_BACKEND = os.getenv('DID_BACKEND', 'rust')

SESSION_COOKIE_AGE = 1209600
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.cases_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


DATABASES = {
    'default': {
        'ENGINE': os.getenv('DATABASE_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DATABASE_NAME', BASE_DIR / 'db.sqlite3'),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Hiver Theme Settings (CSS Variables)
HIVER_THEME = {
    'PRIMARY_COLOR': '#FF8C00',      # Honey-Orange
    'ACCENT_COLOR': '#0064AA',        # Byers Blue
    'DARK_BG': '#1A1A1A',           # Charcoal
    'DARK_TEXT': '#FFFFFF',          # White
    'LIGHT_BG': '#F5F5F5',           # Off-white
    'LIGHT_TEXT': '#333333',         # Dark Gray
}


# Mistral AI Configuration
MISTRAL_API_KEY = os.getenv('MISTRAL_API_KEY', '')

# Celery Configuration
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

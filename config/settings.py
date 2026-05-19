# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

"""
Django settings for Hiver project.

Interactive legal timelines, document archiving, and AI-assisted research.
"""

import os
import platform
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-dev-key-change-in-production")

DEBUG = os.getenv("DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,100.64.0.4").split(",")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "mozilla_django_oidc",
    "apps.core",
    "apps.accounts",
    "apps.timeline",
    "apps.archive",
    "apps.ai_assistant",
    "apps.conversation_logs",
]


MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "mozilla_django_oidc.middleware.SessionRefresh",
    "apps.core.middleware.RustDIDAuthenticationMiddleware",
    "apps.core.middleware.CaseSelectionMiddleware",
    "apps.core.middleware.SessionSecurityMiddleware",
]

ROOT_URLCONF = "config.urls"

LOGIN_URL = "oidc_authentication_init"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"

RUST_DID_LIB_EXTENSION = {"Linux": "so", "Darwin": "dylib", "Windows": "dll"}.get(
    platform.system(), "so"
)

RUST_DID_LIB_PATH = os.getenv(
    "RUST_DID_LIB_PATH",
    BASE_DIR
    / "rust_did"
    / "target"
    / "release"
    / f"libdid_rust.{RUST_DID_LIB_EXTENSION}",
)

DID_BACKEND = os.getenv("DID_BACKEND", "rust")

SESSION_COOKIE_NAME = "hiver_sessionid"
SESSION_COOKIE_AGE = 1209600
SESSION_COOKIE_SECURE = False  # Set to False for development (localhost)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_DOMAIN = None
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_NAME = "hiver_csrftoken"
CSRF_COOKIE_SECURE = False

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.cases_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": os.getenv("DATABASE_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.getenv("DATABASE_NAME", BASE_DIR / "db.sqlite3"),
    }
}


AUTH_PASSWORD_VALIDATORS = []

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.MyOIDCAuthenticationBackend",
]

OIDC_RP_CLIENT_ID = os.getenv("OIDC_RP_CLIENT_ID", "hiver-client")
OIDC_RP_CLIENT_SECRET = os.getenv("OIDC_RP_CLIENT_SECRET", "")
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_RP_VERIFY_KID = False

OIDC_OP_AUTHORIZATION_ENDPOINT = os.getenv("OIDC_OP_AUTHORIZATION_ENDPOINT", "http://127.0.0.1:8000/openid/authorize/")
OIDC_OP_TOKEN_ENDPOINT = os.getenv("OIDC_OP_TOKEN_ENDPOINT", "http://127.0.0.1:8000/openid/token/")
OIDC_OP_USER_ENDPOINT = os.getenv("OIDC_OP_USER_ENDPOINT", "http://127.0.0.1:8000/openid/userinfo/")
OIDC_OP_JWKS_ENDPOINT = os.getenv("OIDC_OP_JWKS_ENDPOINT", "http://127.0.0.1:8000/openid/jwks/")

OIDC_RP_CALLBACK_URL = os.getenv("OIDC_RP_CALLBACK_URL", "http://127.0.0.1:8003/oidc/callback/")

OIDC_USERNAME_ALGO = lambda claims: claims.get("sub")
OIDC_RP_REQUIRED_CLAIMS = []
OIDC_VERIFY_SSL = False
OIDC_STORE_ID_TOKEN = True

CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8003",
]


LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Cache control for development - prevent browser caching of assets
# This ensures the browser always fetches the latest manifest and JS/CSS
if DEBUG:
    # Set cache timeout to 0 for development
    CACHE_MIDDLEWARE_SECONDS = 0
    # Whitenoise max age (if using whitenoise for static files)
    WHITENOISE_MAX_AGE = 0
    # Add security headers to prevent caching in development
    SECURE_BROWSER_XSS_FILTER = False
    SECURE_CONTENT_TYPE_NOSNIFF = False

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Hiver Theme Settings (CSS Variables)
HIVER_THEME = {
    "PRIMARY_COLOR": "#FF8C00",  # Honey-Orange
    "ACCENT_COLOR": "#0064AA",  # Byers Blue
    "DARK_BG": "#1A1A1A",  # Charcoal
    "DARK_TEXT": "#FFFFFF",  # White
    "LIGHT_BG": "#F5F5F5",  # Off-white
    "LIGHT_TEXT": "#333333",  # Dark Gray
}


# Mistral AI Configuration
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")

# Django REST Framework Configuration
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# CORS Configuration (for React frontend in development)
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
CORS_ALLOW_CREDENTIALS = True

# Celery Configuration
CELERY_BROKER_URL = "redis://localhost:6379/0"
CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

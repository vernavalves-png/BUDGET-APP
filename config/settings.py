"""
Django settings for the Budget & Expenditure Approval App.

Environment variables:

Required/production:
    DJANGO_SECRET_KEY
    DJANGO_DEBUG
    DJANGO_ALLOWED_HOSTS
    DATABASE_URL

Optional:
    DJANGO_TIME_ZONE
    CURRENCY_CODE
    SECURE_SSL_REDIRECT

Render:
    Render automatically provides DATABASE_URL and
    RENDER_EXTERNAL_HOSTNAME when configured.
"""

from pathlib import Path

from decouple import config, Csv
import dj_database_url


# =============================================================================
# BASE
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# SECURITY
# =============================================================================

SECRET_KEY = config(
    "DJANGO_SECRET_KEY",
    default="django-insecure-change-me-in-production-6f5b8a3c9d1e",
)

DEBUG = config(
    "DJANGO_DEBUG",
    default=True,
    cast=bool,
)


# =============================================================================
# HOSTS
# =============================================================================

ALLOWED_HOSTS = config(
    "DJANGO_ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=Csv(),
)

# Render provides this automatically for web services.
RENDER_EXTERNAL_HOSTNAME = config(
    "RENDER_EXTERNAL_HOSTNAME",
    default="",
)

if RENDER_EXTERNAL_HOSTNAME:
    if RENDER_EXTERNAL_HOSTNAME not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# =============================================================================
# CSRF
# =============================================================================

CSRF_TRUSTED_ORIGINS = [
    f"https://{host}"
    for host in ALLOWED_HOSTS
    if host not in ("localhost", "127.0.0.1")
]

# Explicitly trust the Render hostname.
if RENDER_EXTERNAL_HOSTNAME:
    render_origin = f"https://{RENDER_EXTERNAL_HOSTNAME}"

    if render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(render_origin)


# =============================================================================
# APPLICATIONS
# =============================================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    "accounts",
    "expenditure",
]


# =============================================================================
# MIDDLEWARE
# =============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # Serve static files efficiently in production.
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# =============================================================================
# URL / WSGI / ASGI
# =============================================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# =============================================================================
# TEMPLATES
# =============================================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",

                "expenditure.context_processors.role_flags",
            ],
        },
    },
]


# =============================================================================
# DATABASE
# =============================================================================
#
# LOCAL:
#     If DATABASE_URL is not set, Django uses SQLite.
#
# RENDER:
#     When DATABASE_URL is set by Render, Django automatically uses
#     PostgreSQL instead.
#
# This means you do NOT need separate settings files for local and Render.
#

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}


# =============================================================================
# PASSWORD VALIDATION
# =============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
        "OPTIONS": {
            "min_length": 8,
        },
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        )
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        )
    },
]


# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = config(
    "DJANGO_TIME_ZONE",
    default="Asia/Dubai",
)

USE_I18N = True
USE_TZ = True


# =============================================================================
# STATIC FILES
# =============================================================================

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },

    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    },
}


# =============================================================================
# MEDIA / UPLOADS
# =============================================================================

MEDIA_URL = "media/"

MEDIA_ROOT = BASE_DIR / "media"


# =============================================================================
# DEFAULT PRIMARY KEY
# =============================================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# =============================================================================
# AUTHENTICATION
# =============================================================================

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "dashboard"

LOGOUT_REDIRECT_URL = "login"


# =============================================================================
# APPLICATION SETTINGS
# =============================================================================

CURRENCY_CODE = config(
    "CURRENCY_CODE",
    default="AED",
)


# =============================================================================
# DJANGO MESSAGE TAGS
# =============================================================================

MESSAGE_TAGS = {
    10: "info",
    20: "info",
    25: "success",
    30: "warning",
    40: "danger",
}


# =============================================================================
# FILE UPLOAD LIMITS
# =============================================================================

# 10 MB maximum upload size.

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024


# =============================================================================
# PRODUCTION SECURITY
# =============================================================================

if not DEBUG:

    SECURE_SSL_REDIRECT = config(
        "SECURE_SSL_REDIRECT",
        default=True,
        cast=bool,
    )

    SESSION_COOKIE_SECURE = True

    CSRF_COOKIE_SECURE = True

    SECURE_BROWSER_XSS_FILTER = True

    SECURE_CONTENT_TYPE_NOSNIFF = True

    X_FRAME_OPTIONS = "DENY"

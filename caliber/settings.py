import json
import logging
import os
import environ

from pathlib import Path

env = environ.Env(DEBUG=(bool, False))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

environ.Env.read_env(os.path.join(BASE_DIR, ".env"))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
for internal_host in ["127.0.0.1", "localhost"]:
    if internal_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(internal_host)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False

AUTH_USER_MODEL = "core.User"
# Reverse proxy / SSL configuration
if env.bool("USE_X_FORWARDED_PROTO", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_COOKIE_NAME = "csrftoken"
CSRF_COOKIE_HTTPONLY = False

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.api",
    "apps.clinvar",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "caliber.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "caliber.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {"default": env.db()}
if DATABASES["default"].get("ENGINE") != "django.db.backends.sqlite3":
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "/caliber/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# File upload limits (default in Django is only 2.5MB, insufficient for large genomic sheets)
DATA_UPLOAD_MAX_MEMORY_SIZE = env.int("DATA_UPLOAD_MAX_MEMORY_SIZE", default=100 * 1024 * 1024)  # 100 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int("FILE_UPLOAD_MAX_MEMORY_SIZE", default=100 * 1024 * 1024)  # 100 MB

STATICFILES_DIRS = [
    BASE_DIR / "static",
    # BASE_DIR / "frontend" / "dist",
]

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

MEDIA_URL = "/caliber/media/"
MEDIA_ROOT = BASE_DIR / "media"

FORCE_SCRIPT_NAME = "/caliber"

LOG_LEVEL = env("LOG_LEVEL", default="INFO").upper()


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line_number": record.lineno,
        }
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_payload)


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json_prod": {
            "()": JSONFormatter,
        },
        "readable_dev": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d]: %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            # Use JSON formatting for production containers, readable text for local debugging
            "formatter": "readable_dev" if DEBUG else "json_prod",
        },
    },
    "loggers": {
        # Root logger captures everything from Django internals
        "": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
        },
        # Dedicated app logger captures fine details from your data pipeline specifically
        "apps.clinvar": {
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": False,  # Prevents double logging back to the root shell handler
        },
    },
}

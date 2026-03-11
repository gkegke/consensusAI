import os
from pathlib import Path
import dj_database_url

# BASE_DIR is /src/
BASE_DIR = Path(__file__).resolve().parent.parent

if os.path.isfile(os.path.join(BASE_DIR, "env.py")):
    import env

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-fallback-key")

DEBUG = os.environ.get("DEBUG", "False") == "True"

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.herokuapp.com']
CSRF_TRUSTED_ORIGINS = ['https://*.herokuapp.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary_storage', 
    'cloudinary',
    
    'core',
    'users',
    'questions',
    'ai_engine',
    'home',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Importance: Critical
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'consensus.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'consensus.wsgi.application'

# <critical importance="10/10">
# Database Configuration: Strictly enforces PostgreSQL for Dev/Prod Parity.
# Developer must provide a DATABASE_URL in the local environment.
# E.g., postgres://myuser:mypassword@localhost:5432/consensus
# </critical>
if os.environ.get("DATABASE_URL"):
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get("DATABASE_URL"))
    }
    print("LOG: Connected to PostgreSQL database.")
else:
    raise Exception("CRITICAL: No DATABASE_URL found! PostgreSQL is strictly required for local and production environments.")


# Static & Media Files Modern Configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'questions': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
        'ai_engine': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}
"""
Django settings for djangoProject27 project.

Generated by 'django-admin startproject' using Django 5.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""
import os
from pathlib import Path
from django.contrib import messages
from celery.schedules import crontab
from dotenv import load_dotenv

# Load .env file
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)
# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-0%7dtqs0j0v-w$p15i1!*#+3ep(%)c1nlw9_0pm--n4yy)2ag%'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["isp.phenom-ventures.com", '127.0.0.1', 'localhost']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'isp.apps.IspConfig',
    'django_celery_results',
    "crispy_forms",
    "crispy_bootstrap5",
    'django.contrib.humanize',
    "rest_framework",
    "corsheaders",
]
CORS_ALLOW_ALL_ORIGINS = True
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'djangoProject27.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
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

WSGI_APPLICATION = 'djangoProject27.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Africa/Nairobi'


USE_I18N = True

USE_TZ = True
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime}  {process:d}  {message}',
            'style': '{',
        },
    },
    'handlers': {
        'newfile': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': './loggers.log',
            'formatter': 'verbose'
        },
    },
    'loggers': {
        '': {
            'level': 'DEBUG',
            'handlers': ['newfile'],
            'propagate': True,
        },
    },
}

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'
LOGIN_URL = ''
# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CELERY_TIMEZONE = "Africa/Nairobi"
CELERY_RESULT_BACKEND = 'django-db'
CELERY_CACHE_BACKEND = 'django-cache'
CELERY_BEAT_SCHEDULE = {
    'check-subscription-every-10-seconds': {
        'task': 'isp.tasks.check_subscription_status',
        'schedule': 30,
    },
    'activate-user': {
        'task': 'isp.tasks.activate_subscription',
        'schedule': 30,
    },
    'remind-subscription': {
        'task': 'isp.tasks.remind_subscription',
        'schedule': crontab(minute = 12 , hour = 12)
    },
}
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

CELERY_BROKER_URL = os.getenv('BROKER_URL')
MESSAGE_TAGS = {
    messages.DEBUG: 'alert-info',
    messages.INFO: 'alert-info',
    messages.SUCCESS: 'alert alert-success alert-dismissible fade show',
    messages.WARNING: 'alert-warning',
    messages.ERROR: 'alert alert-danger alert-dismissible fade show',
}

MPESA_API = {
    "BIZ_SHORT_CODE": os.getenv('BIZ_SHORT_CODE'),
    "CALLBACK_URL": os.getenv('CALLBACK_URL'),
    "CONSUMER_KEY": os.getenv('CONSUMER_KEY'),
    "CONSUMER_SECRET": os.getenv('CONSUMER_SECRET'),
    "CREDENTIALS_URL": os.getenv('CREDENTIALS_URL'),
    "PAYMENT_URL":os.getenv('PAYMENT_URL'),
    "PASS_KEY": os.getenv('PASS_KEY'),
}
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = 'johngachara29@gmail.com'  # Your Gmail email address
EMAIL_HOST_PASSWORD = 'lgwtyehxbdelvmss'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

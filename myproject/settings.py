from pathlib import Path

# --- BASE DIR ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY ---
SECRET_KEY = 'django-insecure-sa14nzjk(&%vtlek)#+r^uyo2se3jturn*xp^0bj%y=*449=p('
DEBUG = True
ALLOWED_HOSTS = ['*']

# --- INSTALLED APPS ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'djoser',
    'django_filters',

    # Local apps
    'product_app',
    'users',
    'order',
    'support',
]

CORS_ALLOWED_ORIGINS = [
    "https://your-frontend-url.vercel.app",
    "http://localhost:5173/",
    "http://127.0.0.1:8000/",


] 

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.storage.CompressedManifestStaticFilesStorage',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

STATIC_URL = '/static/'

# ✅ REQUIRED for Render deployment
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# --- URLS & WSGI ---
ROOT_URLCONF = 'myproject.urls'
WSGI_APPLICATION = 'myproject.wsgi.application'

# --- TEMPLATES ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- DATABASE ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# --- PASSWORD VALIDATORS ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]




# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# --- STATIC FILES ---
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- CUSTOM USER MODEL ---
AUTH_USER_MODEL = 'users.CustomUser'

# --- CORS ---
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
    'x-guest-cart-id',  # <-- add this
]
CORS_ALLOW_ALL_HEADERS = True

# settings.py
RAZORPAY_KEY_ID = 'rzp_test_Rc49M6OPR7fOLP' 
RAZORPAY_KEY_SECRET = 'YnqU7CngK6MOvzwX6TCKTIit' # <-- Replace with your actual Key Secret

# --- REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        
    ),

    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
}

# --- SIMPLE JWT ---
# settings.py
from datetime import timedelta

# --- SIMPLE JWT ---
SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('JWT',),
    
    # 🛑 ADD/UPDATE THIS LINE 🛑
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=360), # Default is only 5 minutes
    
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    # ... any other settings you have
}

# --- DJOSER CONFIG ---
DJOSER = {
    'USER_CREATE_PASSWORD_RETYPE': True,
    'LOGIN_FIELD': 'email',
    'USER_ID_FIELD': 'id',
    'SERIALIZERS': {
        'user_create': 'users.serializers.CustomUserCreateSerializer',
        'user': 'users.serializers.CustomUserSerializer',
        'current_user': 'users.serializers.CustomUserSerializer',
        'token_create': 'djoser.serializers.TokenCreateSerializer',
    }
}


# myproject/settings.py

# ... all your other settings ...

# -----------------------------------------------------------------
# MAILTRAP EMAIL CONFIGURATION (for Development)
# L----------------------------------------------------------------
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'sandbox.smtp.mailtrap.io'
# EMAIL_PORT = 2525  # You can also try 587 if 2525 fails
# EMAIL_HOST_USER = 'd9e3778d341491'  # Your Mailtrap Username
# EMAIL_HOST_PASSWORD = '91e25409152386'  # Paste your actual password here
# EMAIL_USE_TLS = True  # Use TLS


EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'rajagokilavivek@gmail.com'       
EMAIL_HOST_PASSWORD = 'zhju kxtj nhpt vafa'    

# This is the "dummy" From address that will appear in Mailtrap
DEFAULT_FROM_EMAIL = 'MegaCart Support <rajagokilavivek@gmail.com>'

import os

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


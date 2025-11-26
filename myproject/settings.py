# myproject/settings.py

import os
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv() 

# --- BASE DIR ---
BASE_DIR = Path(__file__).resolve().parent.parent


# --- SECURITY ---
SECRET_KEY = 'django-insecure-sa14nzjk(&%vtlek)#+r^uyo2se3jturn*xp^0bj%y=*449=p('
DEBUG = False
ALLOWED_HOSTS = ['*']

# --- INSTALLED APPS ---
INSTALLED_APPS = [
    # Django built-ins
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'cloudinary_storage',
    'django.contrib.staticfiles',
    'cloudinary',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'djoser',
    'django_filters',
    'whitenoise.runserver_nostatic',
   
    

    # Local apps
    'product_app',
    'users',
    'order',
    'support',
    
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ✅ Correct WhiteNoise
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- CORS ---
# CORS_ALLOW_ALL_ORIGINS = True
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
    'x-guest-cart-id',  # optional
]
# CORS_ALLOWED_ORIGINS = True
CORS_ALLOWED_ORIGINS = [
    "https://mega-cart-frontend.vercel.app",
    "http://localhost:5173",
    "http://127.0.0.1:8000",
]
CORS_ALLOW_CREDENTIALS = True

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

# --- URLS & WSGI ---
ROOT_URLCONF = 'myproject.urls'
WSGI_APPLICATION = 'myproject.wsgi.application'

# --- DATABASE ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Use PostgreSQL for prod
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# import os

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': os.environ.get('DB_NAME', 'vetricart_db'),      # Default to local name
#         'USER': os.environ.get('DB_USER', 'root'),              # Default to local user
#         'PASSWORD': os.environ.get('DB_PASSWORD', '123456'),    # Default to local password
#         'HOST': os.environ.get('DB_HOST', '127.0.0.1'),         # Default to localhost
#         'PORT': os.environ.get('DB_PORT', '3306'),
#     }
# }

# --- AUTH ---
AUTH_USER_MODEL = 'users.CustomUser'

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
# settings.py
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# --- DEFAULT AUTO FIELD ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- REST FRAMEWORK ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
    ),
     'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

# --- SIMPLE JWT ---
SIMPLE_JWT = {
    'AUTH_HEADER_TYPES': ('JWT',),
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=360),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}


# DJOSER = {
#     'USER_CREATE_PASSWORD_RETYPE': True,
#     'LOGIN_FIELD': 'email',
#     'USER_ID_FIELD': 'id',
#     'SERIALIZERS': {
#         'user_create': 'users.serializers.CustomUserCreateSerializer',
#         'user': 'users.serializers.CustomUserSerializer',
#         'current_user': 'users.serializers.CustomUserSerializer',
#         'token_create': 'djoser.serializers.TokenCreateSerializer',
#     }
# }

if DEBUG:
    # Local Development
    FRONTEND_DOMAIN = 'localhost:5173'
    PROTOCOL = 'http'
else:
    # Production (Render/Vercel)
    # We hardcode your real domain here so it CANNOT fail
    FRONTEND_DOMAIN = 'mega-cart-frontend.vercel.app'
    PROTOCOL = 'https'
    
DJOSER = {
    # --- YOUR EXISTING SETTINGS ---
    'USER_CREATE_PASSWORD_RETYPE': True,
    'LOGIN_FIELD': 'email',
    'USER_ID_FIELD': 'id',
    'SERIALIZERS': {
        'user_create': 'users.serializers.CustomUserCreateSerializer',
        'user': 'users.serializers.CustomUserSerializer',
        'current_user': 'users.serializers.CustomUserSerializer',
        'token_create': 'djoser.serializers.TokenCreateSerializer',
    },

    # --- NEW PASSWORD RESET LOGIC ---
    
    # 1. The URL structure that will be sent in the email.
    # This must match the Route you added in React (Step 2 of previous answer).
    'PASSWORD_RESET_CONFIRM_URL': 'reset-password/{uid}/{token}',

    # 2. Point to the Custom Email script.
    # This forces the email to use 'localhost:5173' instead of 'localhost:8000'
    'EMAIL': {
        'password_reset': 'users.email.CustomPasswordResetEmail',
    },
    
    # 3. Permissions (Ensure anyone can request a reset without logging in)
    'PERMISSIONS': {
        'password_reset': ['rest_framework.permissions.AllowAny'],
        'password_reset_confirm': ['rest_framework.permissions.AllowAny'],
        'user': ['djoser.permissions.CurrentUserOrAdmin'],
    }
}







# --- RAZORPAY ---
RAZORPAY_KEY_ID = 'rzp_test_RjZJ90FopiN2Lo'
RAZORPAY_KEY_SECRET = '0HOp3DQ9BnbSzE5DFHvixvec'

# # --- EMAIL CONFIGURATION ---
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'rajagokilavivek@gmail.com'
# EMAIL_HOST_PASSWORD = 'eaaw smdg xdtz gnhv'  # Use App Password for Gmail
# DEFAULT_FROM_EMAIL = 'MegaCart Support <rajagokilavivek@gmail.com>'


# import os

# if DEBUG:
#     # ✅ Local development → SMTP works
#     EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#     EMAIL_HOST = 'smtp.gmail.com'
#     EMAIL_PORT = 587
#     EMAIL_USE_TLS = True
#     EMAIL_HOST_USER = 'rajagokilavivek@gmail.com'
#     EMAIL_HOST_PASSWORD = 'kkje supr djoz lqwk'
#     DEFAULT_FROM_EMAIL = f"VetriCart Support <{EMAIL_HOST_USER}>"

# else:
#     # ✅ Render production → SMTP disabled (no crash)
#     EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'




# EMAIL_HOST_USER = os.environ.get('rajagokilavivek@gmail.com')
# EMAIL_HOST_PASSWORD = os.environ.get('kkje supr djoz lqwk')
# DEFAULT_FROM_EMAIL = f"VetriCart Support <{EMAIL_HOST_USER}>"

import os

# 1. Default Sender
# ✅ CORRECT
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', "VetriCart Support <rajagokilavivek@gmail.com>")
SERVER_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', "VetriCart Support <rajagokilavivek@gmail.com>")

# 2. Switch Backends
if not DEBUG:
    # --- PRODUCTION (RENDER) ---
    INSTALLED_APPS += ['anymail']
    EMAIL_BACKEND = "anymail.backends.brevo.EmailBackend"
    
    ANYMAIL = {
        # ✅ FIX: Look for the VARIABLE NAME, not the key itself
        "BREVO_API_KEY": os.environ.get("BREVO_API_KEY"),
    }

else:
    # --- LOCAL DEVELOPMENT ---
    if os.environ.get("USE_SMTP") == "True":
        EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
        EMAIL_HOST = "smtp.gmail.com"
        EMAIL_PORT = 587
        EMAIL_USE_TLS = True
        EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
        EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
    else:
        EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"




import os
from pathlib import Path
from dotenv import load_dotenv

# --- Base Directory ---
BASE_DIR = Path(__file__).resolve().parent.parent

# --- Load environment variables ---
 # Loads variables from .env file

# --- Static Files (CSS, JS) ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# --- Media Files (User Uploads) ---
# This will be overridden by Cloudinary's storage backend
MEDIA_URL = '/media/'

# --- Cloudinary Storage Backend ---
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API_KEY'),
    'API_SECRET': os.getenv('CLOUDINARY_API_SECRET'),
}
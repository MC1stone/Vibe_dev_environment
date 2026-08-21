"""
Django settings for NIR_Mistral Web Application
"""

import os
from pathlib import Path

# Load environment variables (optional - handle missing dotenv gracefully)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-nir-mistral-secret-key-2026')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DJANGO_DEBUG', 'True').lower() == 'true'

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,::1').split(',')

# Application definition
def get_installed_apps():
    """Dynamically build INSTALLED_APPS to handle missing modules gracefully"""
    installed_apps = [
        'django.contrib.admin',
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.messages',
        'django.contrib.staticfiles',
    ]
    
    # Add third-party apps if available
    third_party_apps = ['rest_framework', 'corsheaders', 'rest_framework_simplejwt']
    for app in third_party_apps:
        try:
            __import__(app)
            installed_apps.append(app)
        except ImportError:
            pass
    
    # Add local apps if available
    local_apps = ['core', 'api', 'visualization', 'port_manager']
    for app in local_apps:
        try:
            __import__(app)
            installed_apps.append(app)
        except ImportError:
            pass
    
    return installed_apps

INSTALLED_APPS = get_installed_apps()

def get_middleware():
    """Dynamically build MIDDLEWARE to handle missing modules gracefully"""
    middleware = [
        'django.middleware.security.SecurityMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
        'django.middleware.clickjacking.XFrameOptionsMiddleware',
    ]
    
    # Add optional middleware if available
    optional_middleware = [
        ('corsheaders.middleware.CorsMiddleware', 2),  # Insert after SessionMiddleware
        ('port_manager.middleware.PortConflictResolutionMiddleware', None),  # Append at end
        ('middleware.crewai_middleware.CrewAIMiddleware', None),  # Append at end
    ]
    
    for mw_class, position in optional_middleware:
        try:
            module_path, class_name = mw_class.rsplit('.', 1)
            __import__(module_path)
            if position is not None:
                middleware.insert(position, mw_class)
            else:
                middleware.append(mw_class)
        except ImportError:
            pass
    
    return middleware

MIDDLEWARE = get_middleware()

ROOT_URLCONF = 'nir_web.urls'

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

WSGI_APPLICATION = 'nir_web.wsgi.application'
ASGI_APPLICATION = 'nir_web.asgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# For production PostgreSQL
if os.getenv('DJANGO_DB_ENGINE') == 'postgresql':
    try:
        # Test if we can connect to PostgreSQL
        import psycopg2
        import socket
        
        # First check if the host is reachable
        host = os.getenv('DJANGO_DB_HOST', 'localhost')
        port = int(os.getenv('DJANGO_DB_PORT', '5432'))
        
        # Try to resolve the hostname
        try:
            socket.gethostbyname(host)
        except socket.gaierror:
            # Host cannot be resolved, fall back to SQLite
            pass
        else:
            # Host is resolvable, try to connect
            try:
                psycopg2.connect(
                    host=host,
                    port=port,
                    user=os.getenv('DJANGO_DB_USER', 'nir_user'),
                    password=os.getenv('DJANGO_DB_PASSWORD', 'nir_password_2026'),
                    dbname=os.getenv('DJANGO_DB_NAME', 'nir_mistral')
                )
                DATABASES = {
                    'default': {
                        'ENGINE': 'django.db.backends.postgresql',
                        'NAME': os.getenv('DJANGO_DB_NAME', 'nir_mistral'),
                        'USER': os.getenv('DJANGO_DB_USER', 'nir_user'),
                        'PASSWORD': os.getenv('DJANGO_DB_PASSWORD', 'nir_password_2026'),
                        'HOST': host,
                        'PORT': port,
                    }
                }
            except:
                # Connection failed, fall back to SQLite
                pass
    except ImportError:
        # psycopg2 is not installed, fall back to SQLite
        pass

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators
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
# https://docs.djangoproject.com/en/4.2/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'core.User'

# REST Framework settings
# For development, allow unauthenticated access to API endpoints
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',  # Default to authenticated access
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

# CORS Settings
CORS_ALLOW_ALL_ORIGINS = True  # For development only
CORS_ALLOW_CREDENTIALS = True

# For production
if not DEBUG:
    CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
    CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',')

# NIR Framework Integration
NIR_FRAMEWORK_PATH = os.getenv('NIR_FRAMEWORK_PATH', '/home/martin/Development/vsCode_Environment/NIR_Mistral')
NIR_TEST_ENV_PATH = os.getenv('NIR_TEST_ENV_PATH', f'{NIR_FRAMEWORK_PATH}/NIR_TEST')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Email settings (for password reset, etc.)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@nir-mistral.com')

# Application settings
APP_NAME = 'NIR_Mistral DeveloperAgent Framework'
APP_VERSION = '1.0.0'
APP_DESCRIPTION = 'Advanced NIR Spectroscopy Analysis Platform'

# FlowerAI and Federated Learning Settings
FLOWERAI_ENABLED = os.getenv('FLOWERAI_ENABLED', 'True').lower() == 'true'
FLOWERAI_SERVER_URL = os.getenv('FLOWERAI_SERVER_URL', 'http://flower_server:5555')
FEDERATED_LEARNING_ENABLED = os.getenv('FEDERATED_LEARNING_ENABLED', 'True').lower() == 'true'

# ILIAS Integration Settings
ILIAS_ENABLED = os.getenv('ILIAS_ENABLED', 'True').lower() == 'true'
ILIAS_API_URL = os.getenv('ILIAS_API_URL', 'https://ilias.hswt.de')
ILIAS_CLIENT_ID = os.getenv('ILIAS_CLIENT_ID', 'nir_mistral_client')
ILIAS_CLIENT_SECRET = os.getenv('ILIAS_CLIENT_SECRET', '')

# Terms and Conditions URLs
TERMS_AND_CONDITIONS_URL = os.getenv('TERMS_AND_CONDITIONS_URL', '/terms/')
PRIVACY_POLICY_URL = os.getenv('PRIVACY_POLICY_URL', '/privacy/')

# Quarto Configuration
QUARTO_ENABLED = os.getenv('QUARTO_ENABLED', 'True').lower() == 'true'
QUARTO_PATH = os.getenv('QUARTO_PATH', '/opt/quarto/bin/quarto')

# Ensure Quarto path is correct - check common locations if default not found
if not os.path.exists(QUARTO_PATH):
    # Try common installation locations
    for path in ['/usr/bin/quarto', '/usr/local/bin/quarto', '/opt/quarto/bin/quarto']:
        if os.path.exists(path):
            QUARTO_PATH = path
            break
QUARTO_REPORTS_DIR = os.path.join(BASE_DIR, 'templates', 'reports')
QUARTO_OUTPUT_DIR = os.path.join(BASE_DIR, 'static', 'reports')

# Create reports output directory if it doesn't exist
os.makedirs(QUARTO_OUTPUT_DIR, exist_ok=True)

# Agent Configuration
AGENTS_CONFIG = {
    'spectral_analysis': {
        'enabled': True,
        'timeout': 300,  # 5 minutes
    },
    'metadata_quality': {
        'enabled': True,
        'timeout': 120,  # 2 minutes
    },
    'parameter_recommender': {
        'enabled': True,
        'timeout': 180,  # 3 minutes
    },
    'shift_detector': {
        'enabled': True,
        'timeout': 90,   # 1.5 minutes
    },
    'reporting': {
        'enabled': QUARTO_ENABLED,
        'quarto_path': QUARTO_PATH,
        'output_dir': QUARTO_OUTPUT_DIR,
        'timeout': 300,  # 5 minutes
    }
}
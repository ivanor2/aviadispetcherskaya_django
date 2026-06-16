# django_app/settings.py
import sys
from pathlib import Path
from decouple import config



if getattr(sys, 'frozen', False):
    # Если запущено как скомпилированный exe (onefile)
    # BASE_DIR указывает на временную папку PyInstaller, где лежат шаблоны и статика
    BASE_DIR = Path(sys._MEIPASS)
    # WORKING_DIR указывает на папку, где физически лежит .exe файл (для .env и записи данных)
    WORKING_DIR = Path(sys.executable).parent
else:
    # Если запущено как обычный Python-скрипт
    BASE_DIR = Path(__file__).resolve().parent.parent
    WORKING_DIR = BASE_DIR
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = ['*']

# API настройки
API_BASE_URL = config('API_BASE_URL', default='http://localhost:8001')

# Сессии и аутентификация
SESSION_COOKIE_NAME = 'sessionid'
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = False  # True только если у вас HTTPS
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 3600


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'app.middleware.AuthMiddleware',  # Добавляем кастомный middleware
]

ROOT_URLCONF = 'django_app.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'app.context_processors.user_role',  # Добавляем контекст процессор
            ],
        },
    },
]

WSGI_APPLICATION = 'django_app.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.dummy',
    }
}

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'app' / 'assets']
STATIC_ROOT = WORKING_DIR / 'staticfiles'

LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = 'app:login'
LOGIN_REDIRECT_URL = 'app:index'
LOGOUT_REDIRECT_URL = 'app:login'
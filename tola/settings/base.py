import os
from os.path import abspath, basename, dirname, join, normpath
from sys import path

from django.contrib.messages import constants as message

########## PATH CONFIGURATION
# Absolute filesystem path to the Django project directory:
DJANGO_ROOT = dirname(dirname(abspath(__file__)))


# Absolute filesystem path to the top-level project folder:
SITE_ROOT = dirname(DJANGO_ROOT)

# Site name:
SITE_NAME = basename(DJANGO_ROOT)

# Add our project to our pythonpath, this way we don't need to type our project
# name in our dotted import paths:
path.append(DJANGO_ROOT)
########## END PATH CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = False

########## END DEBUG CONFIGURATION


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('Your Name', 'your_email@example.com'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION



############ MONGO DB #####################
MONGODB_DATABASES = {
    "default": {
        "name": os.getenv("TOLATABLES_MONGODB_NAME"),
        "host": os.getenv("TOLATABLES_MONGODB_HOST", '127.0.0.1'),
        "port": int(os.getenv("TOLATABLES_MONGODB_PORT", 27017)),
        "username": os.getenv("TOLATABLES_MONGODB_USER"),
        "password": os.getenv("TOLATABLES_MONGODB_PASS"),
    },
}
MONGO_URI = 'mongodb://{username}:{password}@{host}:{port}/{db}'.format(
    db=MONGODB_DATABASES['default']['name'],
    username=MONGODB_DATABASES['default']['username'],
    password=MONGODB_DATABASES['default']['password'],
    host=MONGODB_DATABASES['default']['host'],
    port=MONGODB_DATABASES['default']['port'],
)
################ END OF MONGO DB #######################


########## GENERAL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#time-zone
TIME_ZONE = 'America/Los_Angeles'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True
########## END GENERAL CONFIGURATION


########## MEDIA CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = normpath(join(SITE_ROOT, 'media'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'
########## END MEDIA CONFIGURATION


########## STATIC FILE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = normpath(join(SITE_ROOT, 'assets'))

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = (
    normpath(join(SITE_ROOT, 'static')),
)

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
########## END STATIC FILE CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key

########## END SECRET CONFIGURATION


########## SITE CONFIGURATION
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []
########## END SITE CONFIGURATION


########## FIXTURE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    normpath(join(SITE_ROOT, 'fixtures')),
)
########## END FIXTURE CONFIGURATION


########## TEMPLATE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [normpath(join(SITE_ROOT, 'templates')),],
        #'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'tola.context_processors.get_silos',
                'tola.context_processors.google_oauth_settings',
                'tola.context_processors.google_analytics',
            ],
            'builtins': [
                'django.contrib.staticfiles.templatetags.staticfiles',
                'silo.templatetags.underscoretags',
            ],
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ]
        },
    },
]
########## END TEMPLATE CONFIGURATION


########## MIDDLEWARE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#middleware-classes
MIDDLEWARE = (
    # Default Django middleware.
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'tola.middleware.AjaxMessaging.AjaxMessaging',
)
########## END MIDDLEWARE CONFIGURATION


########## END REST CONFIGURATION

########## URL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#root-urlconf
ROOT_URLCONF = '%s.urls' % SITE_NAME
########## END URL CONFIGURATION

# Email setup
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25


########## APP CONFIGURATION
DJANGO_APPS = (
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    'django.contrib.admindocs',
    'social_django',
)

THIRD_PARTY_APPS = (
    'rest_framework',
    'rest_framework.authtoken',
    'crispy_forms',
    'django_extensions',
    'corsheaders',
    'django_celery_results',
    # required by restframework
    'django_filters',
)

#to get a subdirectory to work
path.insert(0, normpath(join(SITE_ROOT, 'datasources')))

# Apps specific for this project go here.
LOCAL_APPS = (
    'silo',
    'tola',
)
DATASOURCE_APPS = (
    'commcare',
    'fileuploadjson',
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS + DATASOURCE_APPS
########## END APP CONFIGURATION

"""
Allowed for now from everyone
CORS_ORIGIN_WHITELIST = (
    "localhost:8000",
    "localhost:4200"
)
"""
CORS_ORIGIN_ALLOW_ALL=True

####### AUTHENTICATION BAKEND CONFIG ##################
# https://github.com/django/django/blob/master/django/contrib/auth/backends.py

AUTHENTICATION_BACKENDS = (
    'social_core.backends.tola.TolaOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.social_user',
    'tola.auth_pipeline.get_or_create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
    'social_core.pipeline.social_auth.associate_by_email',
    'tola.auth_pipeline.user_to_tola',
)

############ END OF AUTHENTICATION BACKEND ##############

########## Login redirect ###########
LOGIN_REDIRECT_URL = '/'
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/'

########## LOGGING CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging

import os
PROJECT_PATH = dirname(dirname(dirname(abspath(__file__))))
path.append(PROJECT_PATH)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'error.log',
        },
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'silo': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'tola': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

########## END LOGGING CONFIGURATION


####### Tola Activity API #######
TOLA_ACTIVITY_API_URL = 'https://tola-activity-demo.mercycorps.org/api/'
TOLA_ACTIVITY_API_TOKEN = 'Token xxxxxxxxxxx'


########## REST CONFIGURATION
# Add Pagination to Rest Framework lists
REST_FRAMEWORK = {
    'PAGINATE_BY': 10,
    'DEFAULT_FILTER_BACKENDS': ('rest_framework.filters.DjangoFilterBackend',),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    )
}

########## WSGI CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = '%s.wsgi.application' % SITE_NAME
########## END WSGI CONFIGURATION

CRISPY_TEMPLATE_PACK = 'bootstrap3'

### This is to map Django message levels to Boostrap3 alert levels ########
MESSAGE_TAGS = {message.DEBUG: 'debug',
                message.INFO: 'info',
                message.SUCCESS: 'success',
                message.WARNING: 'warning',
                message.ERROR: 'danger',}


GOOGLE_REDIRECT_URL = 'http://localhost:8000/oauth2callback/'

########## Celery CONFIGURATION
CELERY_RESULT_BACKEND = 'amqp'
CELERY_CACHE_BACKEND = 'django-cache'

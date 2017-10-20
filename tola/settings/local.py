from os.path import join, normpath
import os
from base import *

#from mongoengine import connect

########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('admin', 'admin@example.org'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

########## END DEBUG CONFIGURATION


########## SECRET CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: REPLACE IT WITH YOUR OWN SECRET_KEY
SECRET_KEY = r"xxxxxxxxxx"
########## END SECRET CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': os.getenv('TOLATABLES_DB_ENGINE'),
        'NAME': os.getenv('TOLATABLES_DB_NAME'),
        'USER': os.getenv('TOLATABLES_DB_USER'),
        'PASSWORD': os.getenv('TOLATABLES_DB_PASS'),
        'HOST': os.getenv('TOLATABLES_DB_HOST'),
        'PORT': int(os.getenv('TOLATABLES_DB_PORT')),
    }
}
"""
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'tolatables',
    }
}"""
############ MONGO DB #####################

import mongoengine

MONGODB_CREDS = {
    'host': os.getenv('TOLATABLES_MONGODB_HOST'),
    'db': os.getenv('TOLATABLES_MONGODB_NAME'),
    'username': os.getenv('TOLATABLES_MONGODB_USER', None),
    'password': os.getenv('TOLATABLES_MONGODB_PASS', None),
    'authentication_source': os.getenv('TOLATABLES_MONGODB_AUTH', None),
    'port': int(os.environ['TOLATABLES_MONGODB_PORT']),
    'alias': 'default'
}

if MONGODB_CREDS['authentication_source']:
    MONGODB_URI = "mongodb://%(username)s:%(password)s@%(host)s/%(db)s?authSource=%(authentication_source)s" % (MONGODB_CREDS)
else:
    MONGODB_URI = MONGODB_CREDS['host']

mongoengine.connect(**MONGODB_CREDS)

################ END OF MONGO DB #######################

########## END DATABASE CONFIGURATION

# Hosts/domain names that are valid for this site
if os.getenv('TOLA_HOSTNAME') is not None:
    ALLOWED_HOSTS = [os.getenv('TOLA_HOSTNAME')]

USE_X_FORWARDED_HOST = True if os.getenv('TOLA_USE_X_FORWARDED_HOST') == 'True' else False

########## GOOGLE CLIENT CONFIG ###########
GOOGLE_REDIRECT_URL = 'http://localhost:8000/oauth2callback/'
#GOOGLE_STEP2_URI = 'http://tola.mercycorps.org/gwelcome'
#GOOGLE_CLIENT_ID = 'xxxxxxx.apps.googleusercontent.com'
#GOOGLE_CLIENT_SECRET = 'xxxxxxxxx'



####### Tola Activity API #######
TOLA_ACTIVITY_API_URL = os.getenv('TOLA_ACTIVITY_API_URL')
TOLA_ACTIVITY_API_TOKEN = os.getenv('TOLA_ACTIVITY_API_TOKEN')

########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION
#Update the logging file handler fo my local mac to be inside project folder
#LOGGING['handlers']['file']['filename'] = "/projects/TolaTables/tolatables_app_error.log"


########## END CACHE CONFIGURATION

#LDAP stuff
LDAP_LOGIN = 'uid=xxx,ou=xxx,dc=xx,dc=xx,dc=xx'
LDAP_SERVER = 'ldaps://xxxx.example.org' # ldap dev
#LDAP_SERVER = 'ldaps://xxxx.example.org' # ldap prod
LDAP_PASSWORD = 'xxxxxx' # ldap dev
#LDAP_PASSWORD = 'xxxxxxx!' # ldap prod
LDAP_USER_GROUP = 'xxxx'
LDAP_ADMIN_GROUP = 'xxxx-xxx'
#ERTB_ADMIN_URL = 'https://xxxx.example.org/xx-xx-dev/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [normpath(join(SITE_ROOT, os.getenv('TOLATABLES_TEMPLATE_DIR'))),],
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
                'tola.context_processors.get_servers',
                'tola.context_processors.get_google_credentials',
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


########## GOOGLE AUTH
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')

SOCIAL_AUTH_MICROSOFT_GRAPH_RESOURCE = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_RESOURCE')
SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_KEY')
SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET')
SOCIAL_AUTH_MICROSOFT_GRAPH_REDIRECT_URL = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_REDIRECT_URL')

ACTIVITY_URL = "http://master.toladatav2.app.tola.io"
TABLES_URL = "http://master.tolatables.app.tola.io"

SOCIAL_AUTH_TOLA_KEY = os.getenv('SOCIAL_AUTH_TOLA_KEY')
SOCIAL_AUTH_TOLA_SECRET = os.getenv('SOCIAL_AUTH_TOLA_SECRET')

GOOGLE_API_KEY = "ReplaceThisWithARealKey"

########## OTHER SETTINGS ###
LOGIN_METHODS = [
    {
        'category_name': 'Tola',
        'targets':
        [
            {
                'name': 'Tola',
                'path': 'tola'
            }
        ]
    },
    {
        'category_name': 'Google',
        'targets':
        [
            {
                'name': 'Google',
                'path': 'google-oauth2'
            }
        ]
    },
    {
        'category_name': 'Microsoft',
        'targets':
        [
            {
                'name': 'Microsoft',
                'path': 'microsoft-graph'
            },
            {
                'name': 'Azure',
                'path': 'azuread-oauth2'
            }
        ]
    },
]

GOOGLE_ANALYTICS_PROPERTY_ID = os.getenv('GOOGLE_ANALYTICS_PROPERTY_ID')


# This allows for additional settings to be kept in a local file
try:
    from local_secret import *
except ImportError:
    pass

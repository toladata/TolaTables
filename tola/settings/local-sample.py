"""Development settings and globals."""


from os.path import join, normpath

from base import *

#from mongoengine import connect

########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('admin', 'admin@yourDomain.org'),
)

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS
########## END MANAGER CONFIGURATION


########## DEBUG CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
TEMPLATE_DEBUG = DEBUG
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
        #'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'xx',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'xx',
        'PASSWORD': 'xx',
        'HOST': 'localhost',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
        'OPTIONS': {'init_command': 'SET default_storage_engine=MYISAM',},
    }
}

############ MONGO DB

import mongoengine

MONGO_CREDS = {
    'host': 'localhost',
    'db': 'myDBName',
    'username': urllib.quote_plus('myUsername'),
    'password': urllib.quote_plus('myPassword'),
    'authentication_source': 'admin',
    'alias': 'default'
}

MONGO_URI = "mongodb://%(username)s:%(password)s@%(host)s/%(db)s?authSource=%(authentication_source)s" % (MONGO_CREDS)

mongoengine.connect(**MONGO_CREDS)

############ END OF MONGO DB

########## END DATABASE CONFIGURATION

########## GOOGLE CLIENT CONFIG ###########
GOOGLE_REDIRECT_URL = 'http://localhost:8000/oauth2callback/'
#GOOGLE_STEP2_URI = 'http://tola.yourDomain.org/gwelcome'
#GOOGLE_CLIENT_ID = 'xxxxxxx.apps.googleusercontent.com'
#GOOGLE_CLIENT_SECRET = 'xxxxxxxxx'


####### Tola Activity API #######
TOLA_ACTIVITY_API_URL = 'https://tola-activity-dev.yourDomain.org/api/'
TOLA_ACTIVITY_API_TOKEN = 'Token xxxxxxxxxxxx'

########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION

########## LOGGING CONFIGURATION
#Optionally update the logging file handler file location
LOGGING['handlers']['file']['filename'] = "/var/log/httpd/tolatables_app_error.log"

########## END LOGGING CONFIGURATION


#LDAP stuff
LDAP_LOGIN = 'uid=xxx,ou=xxx,dc=xx,dc=xx,dc=xx'
LDAP_SERVER = 'ldaps://xxxx.example.org' # ldap dev
#LDAP_SERVER = 'ldaps://xxxx.example.org' # ldap prod
LDAP_PASSWORD = 'xxxxxx' # ldap dev
#LDAP_PASSWORD = 'xxxxxxx!' # ldap prod
LDAP_USER_GROUP = 'xxxx'
LDAP_ADMIN_GROUP = 'xxxx-xxx'
#ERTB_ADMIN_URL = 'https://xxxx.example.org/xx-xx-dev/'


########## GOOGLE AUTH
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = "xxxx.apps.googleusercontent.com"
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = "xxxx"
SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS = "yourDomain.org"
GOOGLE_OAUTH2_CLIENT_SECRETS_JSON = "silo/client_secrets.json"


#Turn On at: https://www.google.com/settings/security/lesssecureapps
# You may also need to unlock captcha: https://accounts.google.com/DisplayUnlockCaptcha
EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'xxxx@yourDomain.org'
EMAIL_HOST_PASSWORD = 'xxxx'
DEFAULT_FROM_EMAIL = 'xxxx@yourDomain.org'
SERVER_EMAIL = "xxxx@yourDomain.org"

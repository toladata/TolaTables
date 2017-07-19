"""Development settings and globals."""


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
        'ENGINE': os.getenv('TOLA_DB_ENGINE'),
        'NAME': os.getenv('TOLA_DB_NAME'),
        'USER': os.getenv('TOLA_DB_USER'),
        'PASSWORD': os.getenv('TOLA_DB_PASS'),
        'HOST': os.getenv('TOLA_DB_HOST'),
        'PORT': int(os.getenv('TOLA_DB_PORT')),
    }
}

############ MONGO DB #####################
import mongoengine
from mongoengine import register_connection
register_connection(alias='default', name='tola')

mongoengine.connect(
    os.getenv('TOLA_MONGODB_NAME'),
    username=os.getenv('TOLA_MONGODB_USER'),
    password=os.getenv('TOLA_MONGODB_PASS'),
    host=os.getenv('TOLA_MONGODB_HOST'),
    port=int(os.getenv('TOLA_MONGODB_PORT')),
    alias='default'
)
################ END OF MONGO DB #######################

########## END DATABASE CONFIGURATION

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


########## GOOGLE AUTH
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')

SOCIAL_AUTH_MICROSOFT_GRAPH_RESOURCE = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_RESOURCE')
SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_KEY')
SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET')
SOCIAL_AUTH_MICROSOFT_GRAPH_REDIRECT_URL = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_REDIRECT_URL')

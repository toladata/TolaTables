"""Development settings and globals."""


from os.path import join, normpath

from base import *

#from mongoengine import connect

########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('admin', 'tola@tola.org'),
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
SECRET_KEY = r"!0^+)=t*ly6ycprf9@kfw$6fsjd0xoh#pa*2erx1m*lp5k9ko7"
########## END SECRET CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
#FOR PRODUCTION USE THIS
#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
#FOR DEV AND TEST
EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
EMAIL_FILE_PATH = '/tmp/tola-messages' # change this to a proper location
########## END EMAIL CONFIGURATION


########## DATABASE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        #'ENGINE': 'django.db.backends.postgresql_psycopg2', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'tola',                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'tola',
        'PASSWORD': '',
        'HOST': 'localhost',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

########## MongoDB Connect

#connect('feeds')

########## END DATABASE CONFIGURATION

########## GOOGLE DOCS REDIRECT CONFIG ###########
GOOGLE_REDIRECT_URL = 'http://localhost:8000/oauth2callback/'

########## GOOGLE AUTH
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = "445847194486-gl2v6ud6ll65vf06vbjaslqqgejad61k.apps.googleusercontent.com"
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = "qAAdNMQy77Vwqgj4YgOu20f7"
SOCIAL_AUTH_GOOGLE_OAUTH2_WHITELISTED_DOMAINS = "mercycorps.org"

########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION



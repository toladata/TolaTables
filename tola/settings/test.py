from base import *

########## GOOGLE AUTH
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY')
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.getenv('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET')
GOOGLE_API_KEY = "ReplaceThisWithARealKey"

########## MICROSOFT AUTH
SOCIAL_AUTH_MICROSOFT_GRAPH_RESOURCE = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_RESOURCE')
SOCIAL_AUTH_MICROSOFT_GRAPH_KEY = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_KEY')
SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_SECRET')
SOCIAL_AUTH_MICROSOFT_GRAPH_REDIRECT_URL = os.getenv('SOCIAL_AUTH_MICROSOFT_GRAPH_REDIRECT_URL')

########## IN-MEMORY TEST DATABASE
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": "",
    },
}
"""Development settings and globals."""

from os.path import join, normpath

SECRET_KEY = r"!0^+)=t*ly6ycprf9@adsfsdfdfsdff#pa*3333*lp5k9ko7"

############ MONGO DB #####################

import mongoengine
try:
    from tola.settings.local_secret import MONGODB_TEST_URI
    MONGODB_URI = MONGODB_TEST_URI
except ImportError:
    MONGODB_URI = 'mongodb://localhost:27017/tola'

mongoengine.connect('tola', MONGODB_URI)

TOLATABLES_MONGODB_NAME = os.environ['TOLATABLES_MONGODB_NAME']

################ END OF MONGO DB #######################


########## MANAGER CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = (
    ('test', 'test@test.com'),
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


########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
########## END EMAIL CONFIGURATION

########## EMAIL SETTINGS

EMAIL_USE_TLS = True
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'test@test.com'
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'test@test.com'
SERVER_EMAIL = "test@test.com"
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
#DEFAULT_TO_EMAIL = 'to email'

########## END EMAIL SETTINGS


########## MongoDB Connect

#connect('feeds')

########## END DATABASE CONFIGURATION

########## GOOGLE CLIENT CONFIG ###########
GOOGLE_STEP2_URI = ''
GOOGLE_CLIENT_ID = ''
GOOGLE_CLIENT_SECRET = ''
GOOGLE_REDIRECT_URL = ''

########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION

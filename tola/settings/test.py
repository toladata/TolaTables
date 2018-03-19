from local import *

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
################ END OF IN-MEMORY TEST DATABASE #######################

############ MONGO DB #####################
MONGODB_DATABASES = {
    "default": {
        "name": "test",
        "host": os.getenv("TOLATABLES_MONGODB_HOST", '127.0.0.1'),
        "port": int(os.getenv("TOLATABLES_MONGODB_PORT", 27017)),
        "username": "test",
        "password": "test",
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
########## END DEBUG CONFIGURATION

########## EMAIL CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = 'test@test.com'

########## END EMAIL CONFIGURATION

########## CACHE CONFIGURATION
# See: https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
########## END CACHE CONFIGURATION

CORS_ORIGIN_ALLOW_ALL = True

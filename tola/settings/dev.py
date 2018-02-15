from local import *

DEV_APPS = (
    'debug_toolbar',
)

INSTALLED_APPS = INSTALLED_APPS + DEV_APPS

DEV_MIDDLEWARE = (
    'debug_toolbar.middleware.DebugToolbarMiddleware',
)

MIDDLEWARE = MIDDLEWARE + DEV_MIDDLEWARE

if os.getenv('TOLA_HOSTNAME') is not None:
    ALLOWED_HOSTS = os.getenv('TOLA_HOSTNAME').split(',')

OFFLINE_MODE = True

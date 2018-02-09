from base import *

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
DEBUG = True if os.getenv('TOLA_DEBUG') == 'True' else False

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
try:
    DATABASES = {
        'default': {
            'ENGINE': os.environ["TOLATABLES_DB_ENGINE"],
            'NAME': os.environ["TOLATABLES_DB_NAME"],
            'USER': os.environ["TOLATABLES_DB_USER"],
            'PASSWORD': os.environ["TOLATABLES_DB_PASS"],
            'HOST': os.environ["TOLATABLES_DB_HOST"],
            'PORT': os.getenv('TOLATABLES_DB_PORT', 5432),
        }
    }
except KeyError:
    # Fallback for tests without environment variables configured
    # Depends on os.environ for correct functionality
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'tolatables',
        }
    }
    print("DATABASES: {}".format(DATABASES))
########## END DATABASE CONFIGURATION

# Hosts/domain names that are valid for this site
if os.getenv('TOLA_HOSTNAME') is not None:
    ALLOWED_HOSTS = [os.getenv('TOLA_HOSTNAME')]

USE_X_FORWARDED_HOST = True if os.getenv('TOLA_USE_X_FORWARDED_HOST') == 'True' else False

########## GOOGLE CLIENT CONFIG ###########
if os.getenv('TABLES_URL') is not None:
    GOOGLE_REDIRECT_URL = os.getenv('TABLES_URL') + '/oauth2callback/'
else:
    GOOGLE_REDIRECT_URL = 'http://localhost:8000/oauth2callback/'
#GOOGLE_STEP2_URI = 'http://tola.mercycorps.org/gwelcome'
#GOOGLE_CLIENT_ID = 'xxxxxxx.apps.googleusercontent.com'
#GOOGLE_CLIENT_SECRET = 'xxxxxxxxx'


if os.getenv('GOOGLE_ANALYTICS') is not None:
    GOOGLE_ANALYTICS = os.getenv('GOOGLE_ANALYTICS')
else:
    GOOGLE_ANALYTICS = None


####### Tola Activity API #######
TOLA_ACTIVITY_API_URL = os.getenv('TOLA_ACTIVITY_API_URL', '')
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

try:
    template_dir = os.environ['TOLATABLES_TEMPLATE_DIR']
except KeyError:
    template_dir ="templates2"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [normpath(join(SITE_ROOT, 'templates2')), ],
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


ACTIVITY_URL = os.getenv('ACTIVITY_URL')
TABLES_URL = os.getenv('TABLES_URL')
TABLES_LOGIN_URL = TOLA_ACTIVITY_API_URL

SOCIAL_AUTH_TOLA_KEY = os.getenv('SOCIAL_AUTH_TOLA_KEY')
SOCIAL_AUTH_TOLA_SECRET = os.getenv('SOCIAL_AUTH_TOLA_SECRET')

from fabric.api import *

# Hosts to deploy onto
env.hosts = ['.toladata.io', '.tola.io']

# Where your project code lives on the server
env.project_root = DJANGO_ROOT

def deploy_static():
    with cd(env.project_root):
        run('./manage.py collectstatic -v0 --noinput')

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')

# GOOGLE_ANALYTICS_PROPERTY_ID = 'A Google Analytics Property ID'

# This allows for additional settings to be kept in a local file
try:
    from local_secret import *
except ImportError:
    pass


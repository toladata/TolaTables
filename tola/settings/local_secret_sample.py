"""Development settings and globals."""

# Any of the settings in base.py and local.py, except for the mongoengine.connect
# settings, and base.py can be overridden here.  In addition, there
# are a few settings shown below that do not appear in the local.py file
# but that are handled by the application.

from os.path import join, normpath



############ MONGO DB

# These settings are used to build the MONGODB_URI connection string used
# by pymongo.  Write tests to the MongoDB database currently clean up after
# themselves so it's possible to use a single DB for testing.  However, future
# versions may use a separate DB for testing, which is why the MONGODB_TEST_URI
# setting is provided.
try:
    MONGODB_CREDS = {
        'host': os.getenv('TOLATABLES_MONGODB_HOST'),
        'db': os.getenv('TOLATABLES_MONGODB_NAME'),
        'username': os.environ['TOLATABLES_MONGODB_USER'],
        'password': os.environ['TOLATABLES_MONGODB_PASS'],
        'authentication_source': os.environ['TOLATABLES_MONGODB_AUTH'],
        'port': int(os.getenv('TOLATABLES_MONGODB_PORT', 27017)),
        'alias': 'default'
    }

    MONGODB_URI = "mongodb://%(username)s:%(password)s@%(host)s:%(port)s/%(db)s?authSource=%(authentication_source)s" % (MONGODB_CREDS)
    MONGODB_TEST_URI = MONGODB_URI

except AttributeError:
    MONGODB_URI = 'mongodb://localhost:27017/tola'


############ END OF MONGO DB

# MySql has a restriction on the length of an index.  These settings will make
# the index short enough to be used in MySql.
SOCIAL_AUTH_ASSOCIATION_SERVER_URL_LENGTH = 200
SOCIAL_AUTH_ASSOCIATION_HANDLE_LENGTH = 125

## The LOGIN_METHODS setting allows for the configuation of login methods.
## The example below is for three login types (Tola, Google, and Microsoft)
## with one of the types (Microsoft) having two login options.
#
# LOGIN_METHODS = [
#     {
#         'category_name': 'Tola',
#         'targets':
#         [
#             {
#                 'name': 'Tola',
#                 'path': 'tola'
#             }
#         ]
#     },
#     {
#         'category_name': 'Google',
#         'targets':
#         [
#             {
#                 'name': 'Google',
#                 'path': 'google-oauth2'
#             }
#         ]
#     },
#     {
#         'category_name': 'Microsoft',
#         'targets':
#         [
#             {
#                 'name': 'Microsoft',
#                 'path': 'microsoft-graph'
#             },
#             {
#                 'name': 'Azure',
#                 'path': 'azuread-oauth2'
#             }
#         ]
#     },
# ]

LOGIN_METHODS = []

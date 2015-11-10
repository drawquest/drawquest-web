import sys
import os.path
import os

def add_to_python_path(path):
    if path not in sys.path:
        sys.path.append(path)

add_to_python_path('/var/canvas/website')

from settings_sentry_common import *
from configuration import Config

CONF_ROOT = os.path.dirname(__file__)

DATABASES = {
    'default': {
        # You can swap out the engine for MySQL easily by changing this value
        # to ``django.db.backends.mysql`` or to PostgreSQL with
        # ``django.db.backends.postgresql_psycopg2``

        # If you change this, you'll also need to install the appropriate python
        # package: psycopg2 (Postgres) or mysql-python
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'sentry',
        'USER': 'sentry',
        'PASSWORD': 'fakepassword',
        'HOST': '',
        'PORT': '3306',
        'OPTIONS': {
            # http://stackoverflow.com/questions/11853141/foo-objects-getid-none-returns-foo-instance-sometimes
            'init_command': 'SET SQL_AUTO_IS_NULL=0;',
        },
    }
}

# If you're expecting any kind of real traffic on Sentry, we highly recommend configuring
# the CACHES and Redis settings

# You'll need to install the required dependencies for Memcached:
#   pip install python-memcached
#
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': ['sentry.foo.example:11211'],
    }
}

# Buffers (combined with queueing) act as an intermediate layer between the database and
# the storage API. They will greatly improve efficiency on large numbers of the same events
# being sent to the API in a short amount of time.

#SENTRY_USE_QUEUE = True
## For more information on queue options, see the documentation for Celery:
## http://celery.readthedocs.org/en/latest/
#BROKER_URL = 'redis://localhost:6379'

## You'll need to install the required dependencies for Redis buffers:
##   pip install redis hiredis nydus
##
#SENTRY_BUFFER = 'sentry.buffer.redis.RedisBuffer'
#SENTRY_REDIS_OPTIONS = {
#    'hosts': {
#        0: {
#            'host': '127.0.0.1',
#            'port': 6379,
#        }
#    }
#}

# You should configure the absolute URI to Sentry. It will attempt to guess it if you don't
# but proxies may interfere with this.
SENTRY_URL_PREFIX = 'https://sentry.example.com'  # No trailing slash!

PRODUCTION = bool(os.path.exists('/etc/canvas'))
PRODUCTION_DEBUG = bool(os.path.exists('/etc/canvas/debug'))
debug = not PRODUCTION or PRODUCTION_DEBUG

SENTRY_WEB_OPTIONS = {
    'workers': 3,  # the number of gunicorn workers
    'secure_scheme_headers': {'X-FORWARDED-PROTO': 'https'},
    'logfile': '/var/canvas/website/run/sentry.gunicorn.log',
    'loglevel': 'debug',
    'debug': debug,
    'daemon': not debug,
    'cpu_count': lambda: os.sysconf('SC_NPROCESSORS_ONLN'),
    'bind': '0.0.0.0:9005',
}

# Mail server configuration

# For more information check Django's documentation:
#  https://docs.djangoproject.com/en/1.3/topics/email/?from=olddocs#e-mail-backends

EMAIL_BACKEND = 'django_ses.SESBackend'
# Used for the django_ses e-mail backend
AWS_ACCESS_KEY_ID = Config['aws']['access_key']
AWS_SECRET_ACCESS_KEY = Config['aws']['secret_key']
DKIM_SELECTOR = 'amazonses'
DKIM_DOMAIN = 'example.com'
DKIM_PRIVATE_KEY_PATH = '/etc/canvas/dkim.private.key'
DKIM_PRIVATE_KEY = open(DKIM_PRIVATE_KEY_PATH).read() if os.path.exists(DKIM_PRIVATE_KEY_PATH) else None

AWS_SES_VERIFY_BOUNCE_SIGNATURES = True
# Domains that are trusted when retrieving the certificate
# used to sign bounce messages.
AWS_SNS_BOUNCE_CERT_TRUSTED_DOMAINS = ['amazonaws.com', 'amazon.com']

DEFAULT_FROM_EMAIL = "passwordreset@example.com"

# http://twitter.com/apps/new
# It's important that input a callback URL, even if its useless. We have no idea why, consult Twitter.
TWITTER_CONSUMER_KEY = ''
TWITTER_CONSUMER_SECRET = ''

# http://developers.facebook.com/setup/
FACEBOOK_APP_ID = ''
FACEBOOK_API_SECRET = ''

# http://code.google.com/apis/accounts/docs/OAuth2.html#Registering
GOOGLE_OAUTH2_CLIENT_ID = ''
GOOGLE_OAUTH2_CLIENT_SECRET = ''

# https://github.com/settings/applications/new
GITHUB_APP_ID = ''
GITHUB_API_SECRET = ''

# https://trello.com/1/appKey/generate
TRELLO_API_KEY = ''
TRELLO_API_SECRET = ''


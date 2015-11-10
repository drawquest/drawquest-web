import os, sys

from settings_common import *

if PRODUCTION:
    SENTRY_WEB_HOST = 'sentry.example.com'
else:
    SENTRY_WEB_HOST = 'localhost'

SENTRY_WEB_PORT = 9005

SENTRY_REMOTE_URL = 'http://{0}:{1}/store/'.format(SENTRY_WEB_HOST, SENTRY_WEB_PORT)

SENTRY_KEY = ''

SENTRY_MAX_LENGTH_STRING = 4000




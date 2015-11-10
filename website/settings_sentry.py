# -*- coding: utf-8 -*-
# Django settings for Sentry.
#
# Make sure to add `--config=/path/to/this/file.py` to `sentry start`.


import hashlib
import os, sys
import os.path
import socket

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from settings_sentry_common import *

#TODO sentry recommends setting this to True, but I can't tell what its security implications are. it's normally a bad idea. it adds sensitive data to the template context. --alex
#TEMPLATE_DEBUG = True

ADMINS = (
    ('canvas', 'sentry@example.com'),
)

INTERNAL_IPS = ('127.0.0.1',)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'sentry.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

#import logging
#logging.basicConfig(level=logging.WARNING)


SENTRY_SEARCH_ENGINE = None
SENTRY_SEARCH_OPTIONS = None

SENTRY_PUBLIC = True


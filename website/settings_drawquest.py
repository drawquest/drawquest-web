from settings import *

PROJECT = 'drawquest'

CANVAS_SUB_SITE = '/admin/'

if PRODUCTION:
    DOMAIN = 'example.com'
    SELF_PORT = 9000
    SELF = 'localhost:9000'
    UGC_HOST = 'i.drawquestugc.com'
    FACEBOOK_APP_ACCESS_TOKEN = None
    FACEBOOK_APP_ID = ''
    FACEBOOK_APP_SECRET = ''
    FACEBOOK_NAMESPACE = 'drawquest'
    TWITTER_APP_KEY = ''
    TWITTER_APP_SECRET = ''
    URBANAIRSHIP_APP_KEY = ''
    URBANAIRSHIP_APP_SECRET = ''
    URBANAIRSHIP_APP_MASTER_SECRET = ''
elif STAGING:
    DOMAIN = 'staging.example.com'
    SELF_PORT = 9000
    SELF = 'localhost:9000'
    UGC_HOST = 'staging.example.com'
    FACEBOOK_APP_ACCESS_TOKEN = None
    FACEBOOK_APP_ID = ''
    FACEBOOK_APP_SECRET = ''
    FACEBOOK_NAMESPACE = 'drawquest-staging'
    TWITTER_APP_KEY = ''
    TWITTER_APP_SECRET = ''
    URBANAIRSHIP_APP_KEY = ''
    URBANAIRSHIP_APP_SECRET = ''
    URBANAIRSHIP_APP_MASTER_SECRET = ''
else:
    DOMAIN = 'dq.savnac.com'
    # We're port forwarding 80 -> 9000
    SELF_PORT = 80
    SELF = 'localhost'
    UGC_HOST = 'dq.savnac.com'
    FACEBOOK_APP_ACCESS_TOKEN = None
    FACEBOOK_APP_ID = ''
    FACEBOOK_APP_SECRET = ''
    FACEBOOK_NAMESPACE = ''
    TWITTER_APP_KEY = ''
    TWITTER_APP_SECRET = ''
    #TODO remove these if we can for dev
    URBANAIRSHIP_APP_KEY = ''
    URBANAIRSHIP_APP_SECRET = ''
    URBANAIRSHIP_APP_MASTER_SECRET = ''

if DRAWQUEST_ADMIN:
    DOMAIN = 'admin.example.com'


UTF8MB4_MYSQL_OPTIONS = {
    # http://stackoverflow.com/questions/11853141/foo-objects-getid-none-returns-foo-instance-sometimes
    'init_command': 'SET NAMES utf8mb4, SQL_AUTO_IS_NULL=0;',
    'charset': 'utf8mb4',
}
MYSQL_OPTIONS = {
    'init_command': 'SET SQL_AUTO_IS_NULL=0;',
}

# To get to the mysql shell:
#    mysql -h <hostname> -u drawquest -p<press enter><paste pw from below>
# Or better yet:
#    dqm dbshell
# Useful commands:
#    See long-running transactions:
#        SHOW ENGINE INNODB STATUS;
#    See all connections:
#        show full processlist\G
if PRODUCTION:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '3306',
            'OPTIONS': UTF8MB4_MYSQL_OPTIONS,
        },
        'content_metadata': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest_content_metadata',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '3306',
            'OPTIONS': MYSQL_OPTIONS,
        },
        'activity': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest',
            'USER': '',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '3306',
            'OPTIONS': MYSQL_OPTIONS,
        },
    }
elif TESTING_USE_MYSQL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest',
            'USER': 'root',
            'PASSWORD': '',
            'HOST': 'localhost',
            'PORT': '',
            'OPTIONS': MYSQL_OPTIONS,
        },
        'content_metadata': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest_content_metadata',
            'USER': 'root',
            'PASSWORD': '',
            'HOST': 'localhost',
            'PORT': '',
            'OPTIONS': MYSQL_OPTIONS,
        }
    }
elif STAGING:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest_staging',
            'USER': 'drawquest',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '3306',
            'OPTIONS': UTF8MB4_MYSQL_OPTIONS,
        },
        'content_metadata': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'drawquest_content_metadata_staging',
            'USER': 'drawquest',
            'PASSWORD': '',
            'HOST': '',
            'PORT': '3306',
            'OPTIONS': MYSQL_OPTIONS,
        },
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/var/canvas/website/drawquest/db.sqlite',
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        },
        'content_metadata': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': '/var/canvas/website/drawquest/db_content_metadata.sqlite',
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

DATABASE_ROUTERS = ['drawquest.dbrouters.DatabaseAppRouter']

if TESTING_USE_MYSQL:
    DATABASE_APPS_MAPPING = {}
elif PRODUCTION:
    DATABASE_APPS_MAPPING = {
        'content_metadata': 'content_metadata',
        'activity': 'activity',
    }
else:
    DATABASE_APPS_MAPPING = {
        'content_metadata': 'content_metadata',
    }

if PRODUCTION or TESTING or STAGING:
    CONN_MAX_AGE = 600

MIDDLEWARE_CLASSES = (
    'drawquest.middleware.PingMiddleware',

    'drawquest.middleware.DrawquestShimMiddleware',

    'drawquest.middleware.Log403Exception',
    'canvas.middleware.ExceptionLogger',
    'canvas.middleware.HandleLoadBalancerHeaders',
    'canvas.middleware.DeferredWorkMiddleware',

    #TODO remove
    'drawquest.middleware.Log403',

    'django.middleware.common.CommonMiddleware',
    'canvas.middleware.UploadifyIsALittleBitchMiddleware',

    'drawquest.apps.drawquest_auth.middleware.SessionHeaderMiddleware',
    'canvas.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',

    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'apps.canvas_auth.middleware.AnonymousUserMiddleware',

    'drawquest.middleware.AppVersionMiddleware',
    'drawquest.middleware.LocaleMiddleware',

    #TODO 'canvas.middleware.RedirectToHttpsMiddleware',

    'canvas.experiments.ForceExperimentMiddleware',
    'canvas.middleware.FacebookMiddleware',
    'canvas.middleware.ImpersonateMiddleware',

    'canvas.middleware.RequestSetupMiddleware',

    'drawquest.middleware.InactiveUserMiddleware',
    'drawquest.middleware.StaffOnlyMiddleware',
    'canvas.middleware.StaffOnlyMiddleware',
    'canvas.middleware.IPHistoryMiddleware',
    'drawquest.middleware.AdminOnAdminServerOnlyMiddleware',

    'canvas.middleware.GlobalExperimentMiddleware',
    'canvas.middleware.HttpRedirectExceptionMiddleware',
    'canvas.middleware.Django403Middleware',
    'canvas.middleware.HttpExceptionMiddleware',

    'canvas.middleware.TimeDilationMiddleware',

    'apps.share_tracking.middleware.TrackShareViewsMiddleware',
    'apps.share_tracking.middleware.TrackClickthroughMiddleware',

    #'django.contrib.messages.middleware.MessageMiddleware',
    'canvas.middleware.ResponseGuard',
)

if DEBUG and not STAGING:
    INTERNAL_IPS = ('127.0.0.1', 'dq.savnac.com', 'staging.example.com',)

    #TODO update debug_toolbar for latest Django.
    #MIDDLEWARE_CLASSES += (
    #    'debug_toolbar.middleware.DebugToolbarMiddleware',
    #)
    #def custom_show_toolbar(request):
    #    if not (DRAWQUEST_ADMIN or DEBUG or STAGING):
    #        return False
    #    if 'debug' in request.GET:
    #        return True
    #    return (request.META.get('HTTP_HOST') in ['admin.example.com', 'dq.savnac.com', 'staging.example.com']
    #            and request.POST.get('format') == 'html')
    #DEBUG_TOOLBAR_CONFIG = {
    #    'INTERCEPT_REDIRECTS': False,
    #    'ENABLE_STACKTRACES': True,
    #    'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
    #    'MEDIA_URL': '/static/lib/',
    #}
    #DEBUG_TOOLBAR_PANELS = (
    #    'debug_toolbar.panels.version.VersionDebugPanel',
    #    'debug_toolbar.panels.timer.TimerDebugPanel',
    #    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    #    'debug_toolbar.panels.headers.HeaderDebugPanel',
    #    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    #    'debug_toolbar.panels.template.TemplateDebugPanel',
    #    'debug_toolbar.panels.sql.SQLDebugPanel',
    #    'debug_toolbar.panels.signals.SignalDebugPanel',
    #    'debug_toolbar.panels.logger.LoggingPanel',
    #    #'debug_toolbar.panels.cache.CacheDebugPanel',
    #    'debug_toolbar.panels.cache2.CachePanel',
    #)

AUTHENTICATION_BACKENDS = (
    'drawquest.apps.drawquest_auth.backends.DrawquestAuthBackend',
)

TEMPLATE_CONTEXT_PROCESSORS = DJANGO_DEFAULT_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request',
    'canvas.context_processors.base_context',
    'apps.features.context_processors.features_context',
    'allauth.account.context_processors.account',
    'allauth.socialaccount.context_processors.socialaccount',
)

ROOT_URLCONF = 'drawquest.urls'

REDIS_HOST = Config['drawquest_redis_host']

# Avoid colliding with example.com redis DBs in testrunner and locally.
if not TESTING:
    REDIS_DB_MAIN = 10
    REDIS_DB_CACHE = 11
    SESSION_REDIS_DB = 12
else:
    REDIS_DB_MAIN = 13
    REDIS_DB_CACHE = 14
    SESSION_REDIS_DB = 15

SESSION_ENGINE = 'drawquest.apps.drawquest_auth.session_backend'
SESSION_COOKIE_AGE = 60*60*24*365
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

MEMCACHE_HOSTS = Config['drawquest_memcache_hosts']

# Bump this to wipe out all caches which use cachecow.
CACHE_KEY_PREFIX = 'DQv7'

if PRODUCTION or STAGING:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
            'LOCATION': Config['drawquest_memcache_hosts'],
            'KEY_PREFIX': CACHE_KEY_PREFIX,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
            'KEY_PREFIX': CACHE_KEY_PREFIX,
        }
    }

LOCALE_PATHS = ('/var/canvas/website/locale',)
ALL_LOCALES = ['en', 'fr', 'de', 'it', 'nl', 'sv', 'es', 'da', 'pt', 'nb', 'he', 'ja', 'ar', 'fi', 'el', 'is', 'mt', 'tr', 'hr', 'zh-Hans', 'zh-Hant', 'ur', 'hi', 'th', 'ko', 'lt', 'pl', 'hu', 'et', 'lv', 'se', 'fo', 'fa', 'ru', 'zh', 'nl', 'ga', 'sq', 'ro', 'cs', 'sk', 'sl', 'yi', 'sr', 'mk', 'bg', 'uk', 'be', 'uz', 'kk', 'az', 'az', 'hy', 'ka', 'mo', 'ky', 'tg', 'tk', 'mn', 'mn', 'ps', 'ku', 'ks', 'sd', 'bo', 'ne', 'sa', 'mr', 'bn', 'as', 'gu', 'pa', 'or', 'ml', 'kn', 'ta', 'te', 'si', 'my', 'km', 'lo', 'vi', 'id', 'tl', 'ms', 'ms', 'am', 'ti', 'om', 'so', 'sw', 'rw', 'rn', 'mg', 'eo', 'cy', 'eu', 'ca', 'la', 'qu', 'gn', 'ay', 'tt', 'ug', 'dz', 'jv', 'su', 'gl', 'af', 'br', 'iu', 'gd', 'gv', 'ga', 'to', 'el', 'kl', 'az', 'nn']
LANGUAGES = (
    ('en', 'English'),
    ('ja', 'Japanese'),
    ('ko', 'Korean'),
    ('zh-Hant', 'Chinese Traditional'),
    ('zh-Hans', 'Chinese Simplified'),
    ('ru', 'Russian'),
    ('fr', 'French'),
    ('th', 'Thai'),
    ('pt', 'Portuguese'),
    ('nl', 'Dutch'),
    ('de', 'German'),
    ('es', 'Spanish'),
)
LOCALES = [language[0] for language in LANGUAGES]

GEOIP_PATH = '/var/canvas/website/static/'

METRICS_ENABLED = False

FACT_HOST = Config['drawquest_fact_host']
FACT_BUCKET = 'drawquest-facts'

IMAGE_FS = Config['drawquest_image_fs']
PLAYBACK_FS = Config['drawquest_playback_fs']

HTTPS_ENABLED = True
UGC_HTTPS_ENABLED = False
API_PROTOCOL = 'https' if HTTPS_ENABLED else 'http'
API_PREFIX = API_PROTOCOL + '://example.com/api/'

TRACKING_ENABLED = PRODUCTION or STAGING

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'drawquest', 'templates'),
    os.path.join(PROJECT_PATH, 'templates'),
)

WSGI_APPLICATION = 'website.wsgi.application'

INSTALLED_APPS = [
    'apps.monkey_patch_django',

    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sitemaps',
    'django.contrib.sites',
    'django.contrib.humanize',
    'django.contrib.messages',

    'south',
    'compressor',
    'debug_toolbar',
    'django_bcrypt',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.facebook_provider',
    'allauth.socialaccount.providers.twitter_provider',

    'apps.activity',
    'apps.analytics',
    'apps.canvas_auth',
    'apps.comments',
    'apps.features',
    'apps.ip_blocking',
    'apps.jinja_adapter',
    'apps.post_thread',
    'apps.share_tracking',
    'apps.signup',
    'apps.user_settings',
    'apps.threads',

    'drawquest.apps.api_console',
    'drawquest.apps.bounces',
    'drawquest.apps.brushes',
    'drawquest.apps.content_metadata',
    'drawquest.apps.drawquest_auth',
    'drawquest.apps.explore',
    'drawquest.apps.feed',
    'drawquest.apps.following',
    'drawquest.apps.gallery',
    'drawquest.apps.iap',
    'drawquest.apps.ios_logging',
    'drawquest.apps.invites',
    'drawquest.apps.palettes',
    'drawquest.apps.playback',
    'drawquest.apps.profiles',
    'drawquest.apps.push_notifications',
    'drawquest.apps.quest_comments',
    'drawquest.apps.quest_invites',
    'drawquest.apps.quest_scheduler',
    'drawquest.apps.quests',
    'drawquest.apps.staff',
    'drawquest.apps.star_gallery',
    'drawquest.apps.stars',
    'drawquest.apps.submit_quest',
    'drawquest.apps.timeline',
    'drawquest.apps.tumblr',
    'drawquest.apps.twitter',
    'drawquest.apps.ugq',
    'drawquest.apps.whitelisting',

    'canvas',
    'drawquest',
]

if DRAWQUEST_SEARCH:
    INSTALLED_APPS += [
        'haystack',
        'drawquest.apps.search',
    ]
    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'drawquest.apps.search.haystack_backends.ConfigurableElasticsearchSearchEngine',
            'URL': 'http://127.0.0.1:9200/',
            'INDEX_NAME': 'haystack',
        },
    }
    #ELASTICSEARCH_INDEX_SETTINGS = {
    #    # index settings
    #}
    #ELASTICSEARCH_DEFAULT_ANALYZER = 'fuzzy'

INSTALLED_APPS += ['raven.contrib.django.raven_compat']

if PRODUCTION or STAGING:
    RAVEN_CONFIG = {
        'dsn': 'http://80941142c78b45b7bb3bbff76faacf6e:23b3334c52484314a601d2b0dd67c0a2@ip-10-164-27-138.ec2.internal:9005/2',
    }
else:
    RAVEN_CONFIG = {
        'dsn': 'http://80941142c78b45b7bb3bbff76faacf6e:23b3334c52484314a601d2b0dd67c0a2@sentry.example.com/2',
    }

    INSTALLED_APPS += ['django_nose']
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = ['--exclude=compressor', '-d']

MINIFY_HTML = False

COMPRESS_ENABLED = False
COMPRESS_OFFLINE = False

# https://docs.djangoproject.com/en/1.5/topics/logging/
# http://help.papertrailapp.com/kb/configuration/configuring-centralized-logging-from-python-apps
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'simple': {
            'format': '%(asctime)s - %(levelname)s - %(message)s',
        },
        'papertrail': {
            'format': '<22>%(asctime)s django: %(levelname)s %(message)s',
        },
        'papertrail_ios': {
            'format': '%(ios_time)s iPad drawquest.app[%(process)d]: %(levelname)s %(message)s',
        },
    },
    'handlers': {
        'local_file': {
            'level': logging.INFO if (PRODUCTION or STAGING) else logging.DEBUG,
            'class': 'logging.FileHandler',
            'filename': os.path.join(PROJECT_PATH, 'run/gunicorn.log'),
            'mode': 'a',
            'formatter': 'simple',
        },
        'papertrail': {
            'level': logging.DEBUG,
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'simple',
            'address': ('logs.papertrailapp.com', 27333),
        },
        'papertrail_ios': {
            'level': logging.DEBUG,
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'papertrail_ios',
            'address': ('logs.papertrailapp.com', 27889),
        },
    },
    'filters': {
    },
    'loggers': {
        'ios_logger': {
            'handlers': ['papertrail_ios'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'papertrail': {
            'handlers': ['papertrail'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['local_file'],
    },
}

DKIM_SELECTOR = 'amazonses'
DKIM_DOMAIN = 'example.com'
DKIM_PRIVATE_KEY_PATH = '/etc/canvas/dkim.private.key'
DKIM_PRIVATE_KEY = open(DKIM_PRIVATE_KEY_PATH).read() if os.path.exists(DKIM_PRIVATE_KEY_PATH) else None

AWS_SES_VERIFY_BOUNCE_SIGNATURES = True
# Domains that are trusted when retrieving the certificate
# used to sign bounce messages.
AWS_SNS_BOUNCE_CERT_TRUSTED_DOMAINS = ['amazonaws.com', 'amazon.com']

# For now, because the password reset template in Django 1.2 is dumb and doesn't take a from_email
DEFAULT_FROM_EMAIL = "passwordreset@example.com"
UPDATES_EMAIL = "DrawQuest <updates@example.com>"

INCLUDE_ERROR_TYPE_IN_API = True

STAR_STICKER_TYPE_ID = 9001

ACTIVITY_TYPE_CLASSES = [
    'apps.activity.redis_models.FollowedByUserActivity',
    'drawquest.activities.StarredActivity',
    'drawquest.activities.PlaybackActivity',
    'drawquest.activities.FolloweePostedActivity',
    'drawquest.activities.FolloweeCreatedUgqActivity',
    'drawquest.activities.WelcomeActivity',
    'drawquest.activities.FeaturedInExploreActivity',
    'drawquest.activities.FacebookFriendJoinedActivity',
    'drawquest.activities.TwitterFriendJoinedActivity',
    'drawquest.activities.NewColorAlertActivity',
]

IPHONE_ACTIVITY_TYPE_CLASSES = [
    'apps.activity.redis_models.FollowedByUserActivity',
    'drawquest.activities.StarredActivity',
    'drawquest.activities.PlaybackActivity',
    'drawquest.activities.WelcomeActivity',
    'drawquest.activities.FeaturedInExploreActivity',
    'drawquest.activities.FacebookFriendJoinedActivity',
    'drawquest.activities.TwitterFriendJoinedActivity',
    'drawquest.activities.NewColorAlertActivity',
]


# Behavioral options.
FEED_ENABLED = True
ALLOW_HIDING_OWN_COMMENTS = False

IAP_VERIFICATION_URL = 'https://buy.itunes.apple.com/verifyReceipt'
IAP_VERIFICATION_SANDBOX_URL = 'https://sandbox.itunes.apple.com/verifyReceipt'

TUMBLR_OAUTH_CONSUMER_KEY = ''
TUMBLR_SECRET_KEY = ''

API_CSRF_EXEMPT = True

EMAIL_CHANNEL_ACTIONS = {
    'recipient': ['first_starred'],
    'actor': ['newsletter'],
}

#TODO replace with something for realtime instead
HTML_APIS_ENABLED = False

QUEST_IDEAS_USERNAME = 'QuestIdeas'


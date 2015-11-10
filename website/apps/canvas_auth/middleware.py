import base64
from functools import wraps

from django.contrib.auth.models import AnonymousUser as DjangoAnonymousUser, User as DjangoUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse

from apps.canvas_auth.backends import authenticate
from apps.canvas_auth.models import AnonymousUser, User
from canvas.view_helpers import forbidden_response
from django.conf import settings


class AnonymousUserMiddleware(object):
    """ Replaces request.user with our own AnonymousUser instead of Django's (if request.user is anonymous). """
    def process_request(self, request):
        if isinstance(request.user, DjangoAnonymousUser):
            request.user = AnonymousUser()


class SessionMigrationMiddleware(object):
    """
    Migrates the "_auth_backend_model" field in user sessions to the first backend listed in AUTHENTICATION_BACKENDS.
    Does nothing if AUTHENTICATION_BACKENDS is empty.

    Must come after "django.middleware.SessionMiddleware", and before
    "django.contrib.auth.middleware.AuthenticationMiddleware".
    """
    BACKEND_KEY = '_auth_user_backend'

    def process_request(self, request):
        if settings.AUTHENTICATION_BACKENDS:
            auth_backend = settings.AUTHENTICATION_BACKENDS[0]

            if request.session.get(self.BACKEND_KEY, auth_backend) != auth_backend:
                request.session['_old_auth_user_backend'] = request.session[self.BACKEND_KEY]
                request.session[self.BACKEND_KEY] = auth_backend


import re

from django.conf import settings
from django.contrib.auth import logout
from django.http import HttpResponseRedirect, HttpResponse
from django.core.exceptions import PermissionDenied

from canvas import util
from drawquest.apps.drawquest_auth.inactive import inactive_user_http_response


class PingMiddleware(object):
    """ Special handling for the ping call. This skips the rest of the middleware. """
    def process_request(self, request):
        # If this is not a ping call, then continue through the rest of the middleware.
        if "/ping" != request.path_info:
            return

        return HttpResponse("pong")


class DrawquestShimMiddleware(object):
    """ Shim for integrating into the Canvas codebase. """
    def process_request(self, request):
        request.is_mobile = False


class StaffOnlyMiddleware(object):
    def process_request(self, request):
        if (request.META['PATH_INFO'].startswith('/admin')
                and not (request.user.is_authenticated()
                         and request.user.is_staff)):
            return HttpResponseRedirect('/login')


class InactiveUserMiddleware(object):
    def process_request(self, request):
        if request.user.is_authenticated() and not request.user.is_active:
            if (request.META['PATH_INFO'].startswith('/api')
                    or request.META['HTTP_HOST'] in ['api.example.com', 'api.staging.example.com']):
                #TODO this is duplicating _handle_json_response work
                return inactive_user_http_response()
            else:
                logout(request)
                return HttpResponseRedirect('/')


class AppVersionMiddleware(object):
    @classmethod
    def get_version_from_user_agent(cls, user_agent):
        if not user_agent:
            return

        m = re.search(r'DrawQuest(-staging)?/([0-9.]+)\b', user_agent)
        if m is not None:
            return m.group(2)

    def process_request(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT')
        version = self.get_version_from_user_agent(user_agent)
        request.app_version = version

        try:
            request.app_version_tuple = tuple([int(v) for v in version.split('.')])
        except (ValueError, AttributeError):
            request.app_version_tuple = None
        
        if version is not None and request.user.is_authenticated():
            request.user.kv.last_app_version.set(version)

        request.idiom = request.META.get('HTTP_X_IDIOM')


class LocaleMiddleware(object):
    def process_request(self, request):
        language_code = request.LANGUAGE_CODE

        if language_code is not None and request.user.is_authenticated():
            request.user.kv.last_language_code.set(language_code)


class AdminOnAdminServerOnlyMiddleware(object):
    def process_request(self, request):
        if (settings.PRODUCTION and request.META['PATH_INFO'].startswith('/admin') 
                and not (settings.DRAWQUEST_ADMIN or settings.DRAWQUEST_SEARCH)):
            return HttpResponse('Update your bookmarks! Use https://admin.example.com')


class Log403Exception(object):
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            import traceback
            import sys
            stack = str(request.path_info) + '\n'

            #stack += request.body + '\n'

            if request.user.is_authenticated():
                stack += request.user.username + '\n'

            import time
            stack += str(time.time()) + '\n'

            import re
            regex_http_          = re.compile(r'^HTTP_.+$')
            regex_content_type   = re.compile(r'^CONTENT_TYPE$')
            regex_content_length = re.compile(r'^CONTENT_LENGTH$')

            request_headers = {}
            for header in request.META:
                if regex_http_.match(header) or regex_content_type.match(header) or regex_content_length.match(header):
                    request_headers[header] = request.META[header]

            stack += '\n'.join('{}: {}'.format(k,v) for k,v in request_headers.items()) + '\n'

            import traceback
            tb = traceback.format_exc()
            stack += unicode(tb)

            stack += '\n'.join('{}: {}'.format(k,v) for k,v in request.COOKIES.items()) + '\n'

            stack += '\n'.join(traceback.format_exception(*sys.exc_info()))

            stk = traceback.extract_stack()
            for mod, lineno, fun_name, call_code_text in stk:
                stack += "[%s:%i] in %s" % (mod, lineno, fun_name)

            from django.core.mail import send_mail
            send_mail('403 stack trace', stack, 'passwordreset@example.com',
                      ['alex@example.com'], fail_silently=False)


class Log403(object):
    def process_response(self, request, response):
        if response.status_code == 403 and request.META.get('HTTP_X_SESSIONID'):
            import traceback
            import sys
            stack = str(request.path_info) + '\n'

            #stack += request.body + '\n'

            if request.user.is_authenticated():
                stack += request.user.username + '\n'

            import time
            stack += str(time.time()) + '\n'

            import re
            regex_http_          = re.compile(r'^HTTP_.+$')
            regex_content_type   = re.compile(r'^CONTENT_TYPE$')
            regex_content_length = re.compile(r'^CONTENT_LENGTH$')

            request_headers = {}
            for header in request.META:
                if regex_http_.match(header) or regex_content_type.match(header) or regex_content_length.match(header):
                    request_headers[header] = request.META[header]

            stack += '\n'.join('{}: {}'.format(k,v) for k,v in request_headers.items()) + '\n'

            import traceback
            tb = traceback.format_exc()
            stack += unicode(tb)

            stack += '\n'.join('{}: {}'.format(k,v) for k,v in request.COOKIES.items()) + '\n'
            stack += '\n' + unicode(response.content)

            stack += '\n'.join(traceback.format_exception(*sys.exc_info()))

            stk = traceback.extract_stack()
            for mod, lineno, fun_name, call_code_text in stk:
                stack += "[%s:%i] in %s" % (mod, lineno, fun_name)

            from django.core.mail import send_mail
            send_mail('403 stack trace', stack, 'passwordreset@example.com',
                      ['alex@example.com'], fail_silently=False)

            user_agent = request.META.get('HTTP_USER_AGENT')
            version = AppVersionMiddleware.get_version_from_user_agent(user_agent)
            if version is None or version in ['1.0.1', '1.0.2']:
                return response

            response = {'success': False, 'error_type': 'ServiceError', 'reason': 'Sorry! To fix your app, please sign-out and sign-in again: tap Profile, tap the gear icon in the top right, then tap Sign Out. Please contact us if you need more help: support@example.com'}

            #if 'activities' in request.META['PATH_INFO']:
            #    response = {'success': True, 'activities': []}
            #else:
            #    response = {'success': False, 'error_type': 'ServiceError', 'reason': 'Error code 403, please try again.'}
            return HttpResponse(util.client_dumps(response), mimetype='application/json')
        return response


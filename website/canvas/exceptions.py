import django.core.exceptions

from django.conf import settings


class ServiceErrorMixin(object):
    def to_json(self):
        ret = {'success': False}

        if settings.INCLUDE_ERROR_TYPE_IN_API:
            ret['error_type'] = self.__class__.__name__

        ret.update(self._to_json())
        return ret

class ServiceError(Exception, ServiceErrorMixin):
    def __init__(self, reason):
        Exception.__init__(self, reason)
        self.reason = reason
        
    def _to_json(self):
        return {'reason': self.reason}

class ResponseTooLarge(ServiceError):
    pass

class DeactivatedUserError(ServiceError):
    status_code = 403

class InsufficientPrivileges(ServiceError):
    def __init__(self):
        ServiceError.__init__(self, "Insufficient privileges.")
        
class NotLoggedIntoFacebookError(ServiceError):
    def __init__(self):
        ServiceError.__init__(self, reason="Not logged in to Facebook")
    
    def to_json(self):
        json = ServiceError.to_json(self)
        json['action'] = 'prompt_facebook_login'
        return json

class HttpRedirect(Exception):
    def __init__(self, redirect_to):
        self.redirect_to = redirect_to

class ValidationError(django.core.exceptions.ValidationError, ServiceErrorMixin):
    def __init__(self, message, code=None, params=None):
        """ ValidationError can be passed any object that can be printed (usually a string), or a dictionary. """
        if isinstance(message, dict):
            self.error_dict = message
        else:
            self.code = code
            self.params = params
            self.message = message
            self.error_list = [self]

    def _to_json(self):
        ret = {}
        if hasattr(self, 'error_dict'):
            ret['errors'] = self.message_dict
        else:
            ret['reason'] = '\n'.join(self.messages)
        return ret

class InvalidFacebookAccessToken(ServiceError):
    pass


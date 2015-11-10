import simplejson

from django.utils.encoding import force_text
from django.utils.functional import Promise


loads = simplejson.loads # For symmetry. 
JSONDecodeError = simplejson.JSONDecodeError

def backend_dumps(things, **kwargs):
    def convert_object(obj):
        if hasattr(obj, 'to_backend'):
            return obj.to_backend()
        elif hasattr(obj, 'to_client'):
            return obj.to_client()
        elif isinstance(obj, Promise):
            return force_text(obj)
        else:
            raise Exception("Unjsonable object of type %r (%r)" % (type(obj), obj))

    return simplejson.dumps(things,
                            default = convert_object,
                            **kwargs)

def dumps(things, **kwargs):
    """
    Dumps `things` into JSON.

    Note that we use the "default" parameter in json.dumps to use the to_dict implementation, if defined, on
    objects to convert them to JSON.

    Defaults to to_client if to_dict doesn't exist, as a fallback.
    """
    def convert_object(obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, 'to_client'):
            return obj.to_client()
        elif isinstance(obj, Promise):
            return force_text(obj)
        raise Exception("Unjsonable object of type %r (%r)" % (type(obj), obj))

    return simplejson.dumps(things,
                            default = convert_object,
                            **kwargs)

def client_dumps(obj, viewer=None, **kwargs):
    """ Dumps `obj.to_client()` (or just `obj` as a fallback) into JSON, for client-side consumption. """
    thing = getattr(obj, 'to_client', lambda: obj)()

    def default(obj):
        if hasattr(obj, 'to_client'):
            return obj.to_client(viewer=viewer)
        elif isinstance(obj, Promise):
            return force_text(obj)
        raise TypeError

    return simplejson.dumps(thing,
                            default=default,
                            **kwargs)


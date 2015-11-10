import base64
import cPickle as pickle

from django.conf import settings
from django.contrib.sessions.backends.cached_db import KEY_PREFIX
from django.contrib.sessions.backends.cached_db import SessionStore as DjangoCachedDBSessionStore
from django.contrib.sessions.models import Session
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from django.utils.encoding import force_unicode
from hashlib import md5


class SessionStore(DjangoCachedDBSessionStore):
    def new_style_decode(self, session_data):
        return DjangoCachedDBSessionStore().decode(session_data)

    def encode(self, session_dict):
        """
        Returns the given session dictionary pickled and encoded as a string.
        """
        pickled = pickle.dumps(session_dict)
        pickled_md5 = md5(pickled + settings.SECRET_KEY).hexdigest()
        return base64.encodestring(pickled + pickled_md5)

    def _old_decode(self, session_data):
        encoded_data = base64.decodestring(session_data)
        pickled, tamper_check = encoded_data[:-32], encoded_data[-32:]
        if md5(pickled + settings.SECRET_KEY).hexdigest() != tamper_check:
            from django.core.exceptions import SuspiciousOperation
            raise SuspiciousOperation("User tampered with session cookie.")
        try:
            return pickle.loads(pickled)
        # Unpickling can cause a variety of exceptions. If something happens,
        # just return an empty dictionary (an empty session).
        except:
            return {}

    def decode(self, session_data):
        try:
            return self._old_decode(session_data)
        except SuspiciousOperation as e:
            try:
                return self.new_style_decode(session_data)
            except SuspiciousOperation:
                raise e

    def load(self):
        try:
            data = cache.get(self.cache_key, None)
        except Exception:
            # Some backends (e.g. memcache) raise an exception on invalid
            # cache keys. If this happens, reset the session. See #17810.
            data = None

        if data is None:
            # Duplicate DBStore.load, because we need to keep track
            # of the expiry date to set it properly in the cache.
            try:
                s = Session.objects.get(session_key=self.session_key)
                data = self.decode(s.session_data)
                cache.set(self.cache_key, data,
                    self.get_expiry_age(expiry=s.expire_date))
            except (Session.DoesNotExist, SuspiciousOperation):
                self.create()
                data = {}
        return data

# Monkey-patch Session's decoder.
Session.get_decoded = lambda self: SessionStore().decode(self.session_data)


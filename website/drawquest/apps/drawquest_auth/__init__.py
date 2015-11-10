from django.contrib.sessions.models import Session

from drawquest.apps.drawquest_auth.session_backend import SessionStore


# Monkey-patch Session's decoder.
Session.get_decoded = lambda self: SessionStore().decode(self.session_data)


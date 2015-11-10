import base64

from django.contrib.auth.backends import ModelBackend

from canvas.exceptions import ValidationError
from drawquest.apps.drawquest_auth.models import User, AnonymousUser


def authenticate(username, password):
    if username is None:
        return None

    try:
        user = User.objects.get(username=username)
        if user.check_password(password):
            return user
    except User.DoesNotExist:
        return None

def _get_username_from_email(email):
    if not email:
        return

    try:
        return User.objects.get(email=email).username
    except User.DoesNotExist:
        return


class DrawquestAuthBackend(ModelBackend):
    def authenticate(self, username=None, password=None, email=None):
        if not username and not email:
            return None

        if not username:
            try:
                username = _get_username_from_email(email)
            except User.DoesNotExist:
                return None

        user = authenticate(username, password)

        if user is None and email:
            # Maybe their username is wrong but email is correct.
            try:
                user = authenticate(username=_get_username_from_email(email),
                                    password=password)
            except User.DoesNotExist:
                pass

        if user is None:
            # Maybe they entered an email into the username field?
            try:
                User.objects.get(username=username)
            except User.DoesNotExist:
                try:
                    user = authenticate(username=_get_username_from_email(username),
                                        password=password)
                except ValidationError:
                    # No such username exists.
                    pass

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()


from collections import defaultdict
import string

from django.conf import settings
from django.contrib import auth
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext, ugettext_lazy as _, pgettext_lazy

from canvas import bgwork
from canvas.exceptions import ServiceError, ValidationError
from canvas.models import UserInfo, FacebookUser, Visibility
from canvas.view_guards import require_user, require_staff
from canvas.view_helpers import check_rate_limit
from drawquest import economy
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.details_models import PrivateUserDetails
from drawquest.apps.drawquest_auth.inactive import inactive_user_http_response
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quests.models import Quest
from drawquest.apps.drawquest_auth.models import associate_facebook_account as _associate_facebook_account
from drawquest.apps.push_notifications.models import is_subscribed
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.twitter.models import associate_twitter_account as _associate_twitter_account, TwitterUser, InvalidTwitterAccessToken
from drawquest.models import heavy_state_sync


urlpatterns = []
api = api_decorator(urlpatterns)


def _validate_charset(s):
    try:
        s.decode('ascii')
        return True
    except UnicodeEncodeError:
        return False

@api('username_available')
def username_available(request, username):
    if User.objects.filter(username__iexact=username):
        return {'available': False}

    return {
        'available': True,
    }

@api('email_is_unused')
def email_is_unused(request, email):
    return {'email_is_unused': User.email_is_unused(email)}

@api('signup')
def signup(request, username, password, email,
           facebook_access_token=None,
           twitter_access_token=None, twitter_access_token_secret=None):
    if check_rate_limit(request, username):
        raise ServiceError(_("Too many signup attempts. Wait a minute and try again."))

    if not _validate_charset(username):
        raise ValidationError({
            'username': [_("Usernames can only contain the letters a-z or A-Z, digits, and underscores.")],
        })

    if not _validate_charset(email):
        raise ValidationError({
            'email': [_("Sorry, your email address contains invalid characters. Please remove them and try again.")],
        })

    try:
        return _login(request, password, username=username, email=email)
    except ValidationError:
        pass

    errors = defaultdict(list)

    fb_user = None
    twitter_user = None

    if facebook_access_token:
        fb_user = FacebookUser.get_or_create_from_access_token(facebook_access_token)
    elif twitter_access_token and twitter_access_token_secret:
        twitter_user = TwitterUser.get_or_create_from_access_token(twitter_access_token, twitter_access_token_secret)

    def username_taken():
        # Ugly hack.
        for error in errors['username']:
            if 'taken' in error:
                return

        errors['username'].append(_("Sorry! That username is already taken."))

    if not password:
        errors['password'].append(_("Please enter a password."))

    if not User.validate_password(password):
        errors['password'].append(_(u"Sorry, your password is too short. Please use %(count)d or more characters." % {'count': User.MINIMUM_PASSWORD_LENGTH}))

    if not email:
        errors['email'].append(_("Please enter your email address."))
    elif not User.validate_email(email):
        errors['email'].append(_("Please enter a valid email address."))

    username_error = User.validate_username(username)
    if username_error:
        errors['username'].append(username_error)

    if not User.email_is_unused(email):
        errors['email'].append(_("Sorry! That email address is already being used for an account. Try signing in instead, or use another email address."))

    if errors:
        if fb_user:
            fb_user.delete()
        raise ValidationError(errors)

    try:
        user = User.objects.create_user(username, email, password)
    except IntegrityError:
        username_taken()
        raise ValidationError(errors)

    ui = UserInfo.objects.create(user=user)
    ui.update_hashes()

    if request.app_version is not None:
        user.kv.signup_app_version.set(request.app_version)

    if fb_user:
        fb_user.user = user
        fb_user.save()

        fb_user.notify_friends_of_signup(facebook_access_token)
        fb_user.respond_to_apprequest_invites(facebook_access_token)

        user.migrate_facebook_avatar(request, facebook_access_token)
    elif twitter_user:
        twitter_user.user = user
        twitter_user.save()

        twitter_user.notify_followers_of_signup(twitter_access_token, twitter_access_token_secret)
        twitter_user.auto_follow_from_invite(twitter_access_token, twitter_access_token_secret)

        @bgwork.defer
        def migrate_twitter_avatar():
            user.migrate_twitter_avatar(request, twitter_access_token, twitter_access_token_secret)

    user = auth.authenticate(username=username, password=password)

    # auth.login starts a new session and copies the session data from the old one to the new one
    auth.login(request, user)

    return {
        'user': PrivateUserDetails.from_id(user.id).to_client(),
        'user_bio': user.userinfo.bio_text,
        'user_subscribed_to_starred': is_subscribed(user, 'starred'),
        'comment_count': 0,
        'quest_count': Quest.all_objects.filter(author=user).count(),
        'sessionid': request.session.session_key,
        'migrated_from_canvas_account': False,
        'login': False,
        'heavy_state_sync': heavy_state_sync(request.user, app_version=request.app_version, app_version_tuple=request.app_version_tuple),
    }

def _login_user(request, user):
    if not user.is_active:
        return inactive_user_http_response()

    # This is a total hack because we don't care to write a backend for the above authenticate method.
    user.backend = settings.AUTHENTICATION_BACKENDS[0]

    auth.login(request, user)

    return {
        'user': PrivateUserDetails.from_id(user.id).to_client(),
        'user_bio': user.userinfo.bio_text,
        'user_subscribed_to_starred': is_subscribed(user, 'starred'),
        'comment_count': QuestComment.all_objects.filter(author=user).count(),
        'quest_count': Quest.all_objects.filter(author=user).count(),
        'sessionid': request.session.session_key,
        'login': True,
        'heavy_state_sync': heavy_state_sync(request.user, app_version=request.app_version, app_version_tuple=request.app_version_tuple),
    }

@api('login_with_facebook')
def login_with_facebook(request, facebook_access_token):
    def denied():
        raise PermissionDenied("No DrawQuest user exists for this Facebook account.")

    try:
        fb_user = FacebookUser.get_from_access_token(facebook_access_token)
    except FacebookUser.DoesNotExist:
        denied()

    if fb_user.user is None:
        denied()

    return _login_user(request, fb_user.user)

@api('login_with_twitter')
def login_with_twitter(request, twitter_access_token, twitter_access_token_secret):
    def denied():
        raise PermissionDenied("No DrawQuest user exists for this Twitter account.")

    try:
        twitter_user = TwitterUser.get_from_access_token(twitter_access_token, twitter_access_token_secret)
    except TwitterUser.DoesNotExist:
        denied()

    if twitter_user.user is None:
        denied()

    try:
        return _login_user(request, twitter_user.user)
    except InvalidTwitterAccessToken:
        raise PermissionDenied(_("Invalid Twitter access token, most likely because of revoked access."))

@api('associate_facebook_account')
@require_user
def associate_facebook_account(request, facebook_access_token):
    _associate_facebook_account(request.user, facebook_access_token, request=request)

    if not request.user.kv.facebook_privacy.get():
        return {
            'facebook_url': 'https://facebook.com/{}'.format(request.user.facebookuser.fb_uid),
        }

@api('associate_twitter_account')
@require_user
def associate_twitter_account(request, twitter_access_token, twitter_access_token_secret):
    _associate_twitter_account(request.user, twitter_access_token, twitter_access_token_secret)

    if not request.user.kv.twitter_privacy.get():
        return {
            'twitter_url': 'https://twitter.com/{}'.format(request.user.twitteruser.screen_name),
        }

def _login(request, password, username=None, email=None):
    def wrong_password():
        raise ValidationError({
            'password': [_("The password you entered is incorrect. Please try again (make sure your caps lock is off).")],
        })

    def wrong_username(username):
        raise ValidationError({
            'username': [_(u"""The username you entered, "%(username)s", doesn't exist. Please try again, or enter the email address you used to sign up.""" % {'username': username})],
        })

    if not username and not email:
        raise ValidationError({'username': [_("Username is required to sign in.")]})

    if username is not None and not all(ord(char) < 256 for char in username):
        wrong_username(username)

    user = auth.authenticate(username=username, password=password, email=email)

    if user is None:
        try:
            try:
                User.objects.get(Q(username=username) | Q(email=email) | Q(email=username))
            except User.MultipleObjectsReturned:
                pass
            wrong_password()
        except User.DoesNotExist:
            wrong_username(username)

    if not user.is_active:
        return inactive_user_http_response()

    auth.login(request, user)

    return {
        'user': PrivateUserDetails.from_id(user.id).to_client(),
        'user_bio': user.userinfo.bio_text,
        'user_subscribed_to_starred': is_subscribed(user, 'starred'),
        'comment_count': QuestComment.all_objects.filter(author=user).count(),
        'quest_count': Quest.all_objects.filter(author=user).count(),
        'sessionid': request.session.session_key,
        'migrated_from_canvas_account': False,
        'login': True,
        'heavy_state_sync': heavy_state_sync(request.user, app_version=request.app_version, app_version_tuple=request.app_version_tuple),
    }

@api('login')
def login(request, password, username=None, email=None):
    return _login(request, password, username=username, email=email)

@api('logout')
def logout(request):
    user_details = None
    if request.user.is_authenticated():
        user_details = PrivateUserDetails.from_id(request.user.id).to_client()

    auth.logout(request)

    return {
        'user': user_details,
        'heavy_state_sync': heavy_state_sync(request.user, app_version=request.app_version, app_version_tuple=request.app_version_tuple),
    }

@api('deactivate')
@require_user
def deactivate_user(request):
    """ Sends us an email. """
    subject = "User deactivation request ({})".format(request.user.username)
    admin_url = 'http://example.com/admin/api_console'
    message = "{}\n\n{}\n\n{}".format(request.user.username, request.user.email, admin_url)
    from_ = "support@example.com"
    to = "support@example.com"
    send_mail(subject, message, from_, [to])

@api('actually_deactivate')
@require_user
def actually_deactivate_user(request):
    request.user.deactivate(request.user)

@api('staff_activate')
@require_staff
def auth_staff_activate_user(request, username):
    user = get_object_or_404(User, username=username)
    user.activate(user)

@api('staff_deactivate')
@require_staff
def auth_staff_deactivate_user(request, username):
    user = get_object_or_404(User, username=username)
    user.deactivate(user)


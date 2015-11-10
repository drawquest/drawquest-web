import string

from cachecow.cache import invalidate_namespace
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import signals
from django.utils.translation import ugettext, ugettext_lazy as _, pgettext_lazy
from facebook import GraphAPI, GraphAPIError

from canvas import json, bgwork
from canvas.util import papertrail
from canvas.cache_patterns import CachedCall
from canvas.exceptions import ServiceError
from canvas.models import Content, UserInfo, FacebookUser, UserRedis, Visibility
from canvas.upload import upload_from_url
from configuration import Config
from drawquest import knobs
from drawquest.activities import WelcomeActivity
from website.apps.canvas_auth.models import User as CanvasUser, AnonymousUser


class User(CanvasUser):
    class Meta:
        proxy = True

    def __repr__(self):
        return '<drawquest user: {}>'.format(self.username)

    def delete(self):
        """
        DON'T USE THIS except for in extreme circumstances. Instead, just set is_active=False.
        Has leftover side-effects like not updating follower/following count. Only use this
        if you're prepared to fix it, or do some manual work afterward.
        """
        #raise Exception("Remove this exception first if you're sure you want to do this.")

        from drawquest.apps.playback.models import Playback
        from drawquest.apps.quest_comments.models import QuestComment
        from drawquest.apps.stars.models import Unstar
        from drawquest.apps.iap.models import IapReceipt
        from apps.canvas_auth.models import User as CanvasUser

        #self.activity_set.all().update(actor=None)

        Playback.objects.filter(viewer=self).delete()
        Unstar.objects.filter(user=self).delete()
        IapReceipt.objects.filter(purchaser=self).delete()

        for comment in self.comments.all():
            quest_comment = QuestComment.all_objects.get(pk=comment.pk)
            quest_comment.playbacks.all().delete()
            comment.delete()

        CanvasUser.objects.get(pk=self.pk).delete()

        invalidate_namespace('comments')

    @classmethod
    def validate_username(cls, username, skip_uniqueness_check=False):
        """ Returns None if the username is valid and does not exist. """
        from drawquest.urls import PROTECTED_URLS

        un = username.lower()

        if (un in Config['blocked_usernames']
                or any(fragment in un for fragment in Config['blocked_username_fragments'])
                or any(fragment in un for fragment in Config['autoflag_words'])
                or un in PROTECTED_URLS):
            return _("Sorry, this username is not allowed.")

        if not un:
            return _("Please enter a username.")
        elif len(un) < 3:
            return _("Username must be 3 or more characters.")
        elif len(un) > 16:
            return _("Username must be 16 characters or less.")

        alphabet = string.lowercase + string.uppercase + string.digits + '_'
        if not all(char in alphabet for char in username):
            return _("Usernames can only contain letters, digits and underscores.")

        if not skip_uniqueness_check:
            if cls.objects.filter(username__iexact=username):
                return _("Sorry! This username is taken. Please pick a different username.")

    @classmethod
    def upload_avatar_from_url(cls, request, url):
        resp = upload_from_url(request, url)
        return Content.all_objects.get_or_none(id=resp['content']['id'])

    def migrate_facebook_avatar(self, request, facebook_access_token):
        from drawquest.models import user_profile

        try:
            fb = GraphAPI(facebook_access_token)
            avatar = fb.get_object('me/picture', type='large', redirect='false')['data']
        except (GraphAPIError, IOError,):
            return

        if avatar.get('is_silhouette'):
            return

        self.userinfo.avatar = User.upload_avatar_from_url(request, avatar.get('url'))
        self.userinfo.save()

        self.details.force()
        user_profile.delete_cache(self.username)

    def migrate_twitter_avatar(self, request, twitter_access_token, twitter_access_token_secret):
        from drawquest.models import user_profile
        from drawquest.apps.twitter.models import Twitter, TwitterError

        try:
            avatar_url = Twitter(twitter_access_token, twitter_access_token_secret).avatar_url()
        except TwitterError:
            return

        if avatar_url is None:
            return

        self.userinfo.avatar = User.upload_avatar_from_url(request, avatar_url)
        self.userinfo.save()

        self.details.force()
        user_profile.delete_cache(self.username)

    def _details(self):
        avatar_id = self.id % 9

        def avatar_url(type_, retina=True):
            retina_suffix = '@2x' if retina else ''
            return 'https://{}/static/img/drawquest/avatar_default_{}_{}{}.png'.format(settings.DOMAIN, type_, avatar_id, retina_suffix)

        ret = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'avatar_url': 'https://{}/static/img/drawquest/avatar_default.png'.format(settings.DOMAIN),
            'avatar_urls': {
                'gallery': {
                    '1x': avatar_url('gallery', retina=False),
                    '2x': avatar_url('gallery', retina=True),
                },
                'profile': {
                    '1x': avatar_url('profile', retina=False),
                    '2x': avatar_url('profile', retina=True),
                },
            }
        }

        try:
            if self.userinfo.avatar:
                archive_url = self.userinfo.avatar.details().get_absolute_url_for_image_type('archive')
                gallery_url = self.userinfo.avatar.details().get_absolute_url_for_image_type('gallery')

                ret['avatar_url'] = archive_url

                ret['avatar_urls'] = {
                    'gallery': {
                        '1x': archive_url,
                        '2x': archive_url,
                    },
                    'profile': {
                        '1x': archive_url,
                        '2x': gallery_url,
                    },
                }
        except UserInfo.DoesNotExist:
            pass

        return ret

    @classmethod
    def details_by_id(cls, user_id, promoter=None):
        from drawquest.apps.drawquest_auth.details_models import UserDetails

        if promoter is None:
            promoter = UserDetails

        def inner_call():
            return cls.objects.get(id=user_id)._details()

        return CachedCall(
            'dq:user:{}:details_v11'.format(user_id),
            inner_call,
            14*24*60*60,
            promoter=promoter,
        )

    @classmethod
    def details_by_username(cls, username, promoter=None):
        from drawquest.apps.drawquest_auth.details_models import UserDetails

        if promoter is None:
            promoter = UserDetails

        def inner_call():
            return cls.objects.get(username=username)._details()

        return CachedCall(
            'dq:user:{}:details_v2'.format(username),
            inner_call,
            30*24*60*60,
            promoter=promoter,
        )

    @property
    def details(self):
        return self.details_by_id(self.id)

    def invalidate_details(self):
        self.details.force()
        self.details_by_username(self.username).force()

    def to_client(self, **kwargs):
        return self.details().to_client()

    def comment_count(self, viewer=None):
        from drawquest.apps.quest_comments.models import QuestComment

        if viewer is not None and viewer.is_authenticated() and viewer.id == self.id:
            return QuestComment.objects.filter(author=self, visibility__in=[Visibility.PUBLIC, Visibility.CURATED]).count()

        return QuestComment.objects.filter(author=self, visibility=Visibility.PUBLIC).count()

    def violation_count(self):
        """ Number of times this user's drawings have been removed. """
        from canvas.models import Visibility
        from drawquest.apps.quest_comments.models import QuestComment

        return QuestComment.objects.filter(author=self, judged=True, visibility=Visibility.DISABLED).count()

    def follow(self, user_to_follow):
        super(User, self).follow(user_to_follow)

        if user_to_follow.redis.new_followers.zcard() > knobs.AUTO_MODERATION['followers']:
            user_to_follow.userinfo.trusted = True
            user_to_follow.userinfo.save()

    def following_ids(self):
        return [int(id_) for id_ in self.redis.new_following.zrange(0, -1)]

    def activate(self, activator):
        if self.id != activator.id and not activator.is_staff:
            raise PermissionDenied("Must be staff to deactivate a user.")

        self.is_active = True
        self.save()
        self.details.force()

    def deactivate(self, deactivator):
        if self.id != deactivator.id and not deactivator.is_staff:
            raise PermissionDenied("Must be staff to deactivate a user.")

        for comment in self.comments.all():
            if comment.is_visible():
                comment.moderate_and_save(Visibility.UNPUBLISHED, deactivator, undoing=True)

        self.is_active = False
        self.save()
        self.details.force()


def associate_facebook_account(user, facebook_access_token, request=None):
    try:
        fb_user = FacebookUser.get_or_create_from_access_token(facebook_access_token, request=request)
    except GraphAPIError as e:
        papertrail.debug(u'GraphAPIError inside associate_facebook_account: {} (user: {}, token: {})'.format(e.message, user.username, facebook_access_token))

        raise ServiceError(_("There appears to be an issue communicating with Facebook. Please try again."))

    try:
        existing_fb_user = user.facebookuser

        if existing_fb_user.fb_uid == fb_user.fb_uid:
            return

        existing_fb_user.user = None
        existing_fb_user.save()
    except FacebookUser.DoesNotExist:
        pass

    fb_user.user = user
    fb_user.save()

    @bgwork.defer
    def notify_friends():
        fb_user.notify_friends_of_signup(facebook_access_token)
        fb_user.respond_to_apprequest_invites(facebook_access_token)

def user_post_save(sender, instance, created, **kwargs):
    if created:
        welcome_activity = WelcomeActivity()
        UserRedis(instance.id).activity_stream.push(welcome_activity)
        UserRedis(instance.id).iphone_activity_stream.push(welcome_activity)
signals.post_save.connect(user_post_save, sender=User)


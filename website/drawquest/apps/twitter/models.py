from django.conf import settings
from django.db import models
from rauth.service import OAuth1Service
from raven.contrib.django.raven_compat.models import client
import requests

from apps.share_tracking.models import get_share_page_url_with_tracking
from canvas import bgwork
from canvas.util import papertrail
from canvas.exceptions import ServiceError
from canvas.metrics import Metrics
from canvas.models import BaseCanvasModel
from canvas.notifications.actions import Actions
from drawquest import economy
from drawquest.apps.drawquest_auth.models import User


TWITTER_API_URL = 'https://api.twitter.com/1.1/'

def twitter_service():
    return OAuth1Service(
        name='twitter',
        consumer_key=settings.TWITTER_APP_KEY,
        consumer_secret=settings.TWITTER_APP_SECRET,
        request_token_url='https://api.twitter.com/oauth/request_token',
        access_token_url='https://api.twitter.com/oauth/access_token',
        authorize_url='https://api.twitter.com/oauth/authorize',
    )


class TwitterError(ServiceError):
    def __init__(self, reason=None):
        if reason is None:
            reason = ("There appears to be an issue communicating with Twitter. "
                      "Please try logging in again.")
        super(TwitterError, self).__init__(reason)


class TwitterAccountSuspendedError(TwitterError):
    def __init__(self, reason="Your Twitter account has been suspended, so we can't share to it. Please either change to a new Twitter account, or disable Twitter sharing."):
        super(TwitterAccountSuspendedError, self).__init__(reason)

class TwitterDuplicateStatusError(TwitterError): pass
class TwitterRateLimitError(TwitterError): pass
class InvalidTwitterAccessToken(TwitterError): pass


def _contains_error(json, error_code):
    return 'errors' in json and any(error['code'] == error_code for error in json['errors'])


class Twitter(object):
    def __init__(self, access_token, access_token_secret):
        self.twitter = twitter_service()
        self.access_token = access_token
        self.access_token_secret = access_token_secret

    def call(self, endpoint, params, method='GET'):
        try:
            session = self.twitter.get_session((self.access_token, self.access_token_secret))
            r = session.request(method, TWITTER_API_URL + endpoint, params=params)
            json = r.json()

            # https://dev.twitter.com/docs/rate-limiting/1.1
            if 'errors' in json:
                errors = json['errors']
                status_code = r.status_code

                if status_code == 429 and 88 in [e['code'] for e in errors]:
                    raise TwitterRateLimitError()

            if r.status_code == 401:
                papertrail.debug(u'InvalidTwitterAccessToken error for endpoint {} with JSON response: {}'.format(endpoint, json.__repr__().replace('\n', ' ')))

                raise InvalidTwitterAccessToken()

            r.raise_for_status()

            return json
        except requests.exceptions.HTTPError as e:
            try:
                json = e.response.json()

                if _contains_error(json, 187):
                    raise TwitterDuplicateStatusError()
                elif _contains_error(json, 64):
                    raise TwitterAccountSuspendedError()

                raise TwitterError()
            except ValueError:
                raise TwitterError()

    def account_credentials(self):
        return self.call('account/verify_credentials.json', {
            'include_entitites': False,
            'skip_status': True,
        })

    def avatar_url(self):
        url = self.account_credentials()['profile_image_url']

        if 'default' in url.split('/')[-1]:
            return None

        url = url.replace('_normal', '')

        return url

    def tweet(self, message):
        # https://dev.twitter.com/docs/api/1.1/post/statuses/update
        return self.call('statuses/update.json', {
            'status': message.encode('utf8'),
            'trim_user': True,
        }, method='POST')


class TwitterUser(BaseCanvasModel):
    user = models.OneToOneField(User, null=True, blank=True)
    twitter_uid = models.BigIntegerField(unique=True, blank=False)
    name = models.CharField(max_length=512)
    screen_name = models.CharField(max_length=512)
    invited_by = models.ManyToManyField('self', blank=True, symmetrical=False)

    @classmethod
    def _twitter_credentials(cls, access_token, access_token_secret):
        credentials = Twitter(access_token, access_token_secret).account_credentials()
        return credentials['id_str'], credentials

    @classmethod
    def create_from_access_token(cls, access_token, access_token_secret, twitter_uid=None, credentials=None):
        if twitter_uid is None:
            twitter_uid, credentials = cls._twitter_credentials(access_token, access_token_secret)

        return cls.objects.create(
            twitter_uid=twitter_uid,
            name=credentials['name'],
            screen_name=credentials['screen_name'],
        )

    @classmethod
    def get_from_access_token(cls, access_token, access_token_secret, twitter_uid=None):
        if twitter_uid is None:
            twitter_uid, _ = cls._twitter_credentials(access_token, access_token_secret)
        return cls.objects.get(twitter_uid=twitter_uid)

    @classmethod
    def get_or_create_from_access_token(cls, access_token, access_token_secret):
        twitter_uid, credentials = cls._twitter_credentials(access_token, access_token_secret)

        try:
            return cls.get_from_access_token(access_token, access_token_secret, twitter_uid=twitter_uid)
        except cls.DoesNotExist:
            return cls.create_from_access_token(access_token, access_token_secret, twitter_uid=twitter_uid, credentials=credentials)

    def followers_on_drawquest(self, access_token, access_token_secret):
        follower_ids = Twitter(access_token, access_token_secret).call('followers/ids.json', {
            'user_id': self.twitter_uid,
            'stringify_ids': True,
            'count': 5000,
            'cursor': -1,
        })['ids']
        return TwitterUser.objects.filter(twitter_uid__in=follower_ids)

    def notify_followers_of_signup(self, access_token, access_token_secret):
        from canvas.models import FriendJoinedNotificationReceipt

        if self.user is None:
            raise ValueError("This TwitterUser instance isn't yet associated with a DrawQuest User.")

        followers = self.followers_on_drawquest(access_token, access_token_secret)
        Actions.twitter_friend_joined(self.user, followers)

        FriendJoinedNotificationReceipt.create_receipts_in_bulk(self.user,
                                                                [follower.user for follower in followers])

    def auto_follow_from_invite(self, access_token, access_token_secret):
        for twitter_friend in self.invited_by.all().select_related('user'):
            twitter_friend.user.follow(self.user)
            self.user.follow(twitter_friend.user)


def associate_twitter_account(user, access_token, access_token_secret):
    twitter_user = TwitterUser.get_or_create_from_access_token(access_token, access_token_secret)

    try:
        existing_twitter_user = user.twitteruser

        if existing_twitter_user.twitter_uid == twitter_user.twitter_uid:
            return

        existing_twitter_user.user = None
        existing_twitter_user.save()
    except TwitterUser.DoesNotExist:
        pass

    twitter_user.user = user
    twitter_user.save()

    @bgwork.defer
    def notify_friends():
        twitter_user.notify_followers_of_signup(access_token, access_token_secret)
        twitter_user.auto_follow_from_invite(access_token, access_token_secret)

def tweet_comment(comment, access_token, access_token_secret, request=None):
    quest_url = get_share_page_url_with_tracking(comment, comment.author, 'twitter', absolute=True)

    @bgwork.defer
    def rewards():
        economy.credit_personal_twitter_share(comment.author)

    if comment.parent_comment is None:
        title = comment.title
        message = u'I just created a Quest on @DrawQuest: "{}" Come draw it with me! {}'.format(comment.title, quest_url)
    else:
        message = u'"{}" {} via @DrawQuest'.format(comment.parent_comment.title, quest_url)

    try:
        Twitter(access_token, access_token_secret).tweet(message)
    except (InvalidTwitterAccessToken, TwitterAccountSuspendedError) as e:
        raise e
    except TwitterError:
        client.captureException()

        if request:
            Metrics.share_to_twitter_from_publish_error.record(request, quest=quest_url)


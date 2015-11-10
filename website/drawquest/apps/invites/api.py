from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from canvas.cache_patterns import CachedCall
from canvas.models import FacebookUser
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.details_models import UserDetails
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.twitter.models import TwitterUser

urlpatterns = []
api = api_decorator(urlpatterns)


@api('facebook_friends_on_drawquest')
def facebook_friends_on_drawquest(request, facebook_access_token):
    """ Returns one field, `users`, a list of `User` dicts. """
    fb_user = FacebookUser.get_or_create_from_access_token(facebook_access_token)
    fb_friends = fb_user.friends_on_drawquest(facebook_access_token).select_related('user')

    fb_friend_uids = dict((friend.user_id, friend.fb_uid) for friend in fb_friends)

    users = CachedCall.multicall([User.details_by_id(fb_friend.user_id) for fb_friend in fb_friends
                                  if fb_friend.user_id is not None])


    for user in users:
        user.fb_uid = fb_friend_uids[user.id]

        if request.user.is_authenticated() and request.user.id != user.id:
            user.viewer_is_following = request.user.is_following(user.id)

    return {
        'users': users,
    }

@api('twitter_followers_on_drawquest')
def twitter_followers_on_drawquest(request, twitter_access_token, twitter_access_token_secret):
    """ Returns one field, `users`, a list of `User` dicts. """
    twitter_user = TwitterUser.get_or_create_from_access_token(twitter_access_token, twitter_access_token_secret)
    twitter_friends = twitter_user.followers_on_drawquest(twitter_access_token, twitter_access_token_secret)
    twitter_friends = list(twitter_friends.select_related('user'))

    twitter_friend_uids = dict((friend.user_id, friend.twitter_uid) for friend in twitter_friends)

    users = CachedCall.multicall([User.details_by_id(twitter_friend.user_id) for twitter_friend in twitter_friends
                                  if twitter_friend.user_id is not None])

    for user in users:
        user.twitter_uid = twitter_friend_uids[user.id]

        if request.user.is_authenticated() and request.user.id != user.id:
            user.viewer_is_following = request.user.is_following(user.id)

    return {
        'users': users,
    }

@api('invited_twitter_friends')
@require_user
def invited_twitter_friends(request, twitter_ids):
    for twitter_uid in twitter_ids:
        try:
            friend = TwitterUser.objects.create(twitter_uid=twitter_uid)
        except IntegrityError:
            continue

        friend.invited_by.add(request.user.twitteruser)
        friend.save()


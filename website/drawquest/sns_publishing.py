from django.conf import settings
from facebook import GraphAPIError, GraphAPI
from django.utils.translation import ugettext, ugettext_lazy as _
from raven.contrib.django.raven_compat.models import client

from canvas.util import papertrail
from canvas.exceptions import ServiceError, InvalidFacebookAccessToken
from canvas.metrics import Metrics
from canvas.models import send_email
from drawquest.apps.drawquest_auth.models import User, associate_facebook_account
from drawquest.apps.timeline.models import PendingTimelineShare
from drawquest.apps.twitter.models import (associate_twitter_account, InvalidTwitterAccessToken,
                                           tweet_comment)


def facebook_share_pre_post(request, facebook_access_token):
    if not facebook_access_token:
        raise ServiceError("Can't share to your timeline if you haven't signed into Facebook yet.")

    facebook_share = True

    try:
        associate_facebook_account(request.user, facebook_access_token, request=request)
    except ServiceError:
        papertrail.debug(u'associate_facebook_account failed inside facebook_share_pre_post: (user: {}, token: {}), raising InvalidFacebookAccessToken'.format(request.user.username, facebook_access_token))
        facebook_share = False
        Metrics.facebook_error_during_publish.record(request)

    if request.app_version != '1.0.1':
        try:
            permissions = GraphAPI(facebook_access_token).get_object('me/permissions')['data'][0]
        except GraphAPIError as e:
            papertrail.debug(u'me/permissions failed inside facebook_share_pre_post: {} (user: {}, token: {}), raising InvalidFacebookAccessToken'.format(e.message, request.user.username, facebook_access_token))
            raise InvalidFacebookAccessToken("Invalid Facebook access token, please re-auth with Facebook.")
        except IOError as e:
            papertrail.debug(u'me/permissions failed inside facebook_share_pre_post with IOError: {} (user: {}), disabling facebook_share'.format(e.message, request.user.username))
            facebook_share = False
        else:
            if permissions.get('installed') != 1 or permissions.get('publish_actions') != 1:
                papertrail.debug(u'me/permissions failed inside facebook_share_pre_post because insufficient permissions (user: {}), disabling facebook_share'.format(request.user.username))
                facebook_share = False
                Metrics.facebook_insufficient_permissions_during_publish.record(request)

    return facebook_share

def facebook_share_post_post(request, facebook_access_token, share_obj):
    PendingTimelineShare.objects.create(
        user=request.user,
        comment=share_obj,
        access_token=facebook_access_token,
    ).share(request=request)

def twitter_share_pre_post(request, twitter_access_token, twitter_access_token_secret):
    if not twitter_access_token:
        raise ServiceError("Can't share to Twitter if you haven't signed into Twitter yet.")

    twitter_share = True

    try:
        associate_twitter_account(request.user, twitter_access_token, twitter_access_token_secret)
    except InvalidTwitterAccessToken as e:
        raise e
    except ServiceError:
        twitter_share = False
        Metrics.twitter_error_during_publish.record(request)

    return twitter_share

def twitter_share_post_post(request, twitter_access_token, twitter_access_token_secret, share_obj):
    tweet_comment(share_obj, twitter_access_token, twitter_access_token_secret, request=request)

def _share_by_email(sender, recipients, subject, template_name, context):
    _context = {'sender': sender}
    _context.update(context)

    headers = {'Reply-To': sender.email}

    for recipient in recipients:
        if not User.validate_email(recipient['email']):
            continue

        try:
            send_email(recipient['email'], settings.UPDATES_EMAIL, subject, template_name, _context, headers=headers)
        except Exception, e:
            client.captureException()

def share_quest_by_email(quest, sender, recipients):
    '''
    `recipients` is a list of dicts containing email and name.
    '''
    quest_details = quest.details()
    template_url = ''

    if quest_details.content:
        template_url = quest_details.content.gallery['url']

    return _share_by_email(sender, recipients, _('Someone invited you to complete a Quest on DrawQuest!'), 'quest_share', {
        'quest': quest_details,
        'quest_template_url': template_url,
    })

def share_comment_by_email(comment, sender, recipients):
    from drawquest.apps.quests.details_models import QuestDetails

    quest_details = QuestDetails.from_id(comment.parent_comment_id)
    template_url = ''

    if quest_details.content:
        template_url = quest_details.content.gallery['url']

    return _share_by_email(sender, recipients, _('Someone shared a drawing with you on DrawQuest!'), 'comment_share', {
        'comment': comment.details(),
        'quest': quest_details,
        'quest_template_url': template_url,
    })


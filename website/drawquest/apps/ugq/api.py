from datetime import timedelta as td

from django.conf import settings
from django.shortcuts import get_object_or_404

from canvas import bgwork
from canvas.exceptions import ServiceError
from canvas.forms import validate_and_clean_comment
from canvas.models import Visibility
from canvas.redis_models import RateLimit, RealtimeChannel
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest import knobs, economy
from drawquest import sns_publishing
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quests.models import Quest, archived_quests
from drawquest.apps.ugq import models


urlpatterns = []
api = api_decorator(urlpatterns)


@api('create_quest')
@require_user
def create_quest(request, title, content_id=None, invite_followees=False,
                 facebook_share=False, facebook_access_token=None,
                 twitter_share=False, twitter_access_token=None, twitter_access_token_secret=None,
                 email_share=False, email_recipients=[],
                 resolve_share_ids=[]):
    if not request.user.is_staff and not settings.STAGING:
        prefix = 'user:{}:create_quest_limit:'.format(request.user.id)
        if not RateLimit(prefix+'h', 60, 60*60).allowed() or not RateLimit(prefix+'d', 100, 8*60*60).allowed():
            raise ServiceError("Attempting to create quests too quickly.")

    _, _, content, _, title = validate_and_clean_comment(
        request.user,
        parent_comment=None,
        reply_content=content_id,
        title=title,
    )

    if facebook_share:
        facebook_share = sns_publishing.facebook_share_pre_post(request, facebook_access_token)

    if twitter_share:
        twitter_share = sns_publishing.twitter_share_pre_post(request, twitter_access_token, twitter_access_token_secret)

    quest = Quest.create_and_post(request, request.user, title, content=content, ugq=True)

    models.autocurate_for_flag_words(quest)

    if invite_followees:
        quest.invited_users.invite(request.user, request.user.followers(), ignore_errors=True)

    if facebook_share:
        sns_publishing.facebook_share_post_post(request, facebook_access_token, quest)

    if twitter_share:
        sns_publishing.twitter_share_post_post(request, twitter_access_token, twitter_access_token_secret, quest)

    for share_id in resolve_share_ids:
        share = ShareTrackingUrl.objects.get(id=share_id)

        if share.redirect_url:
            pass #TODO log some error here without failing this request
        
        share.redirect_url = quest.get_share_page_url()
        share.save()

    if email_share:
        @bgwork.defer
        def defer_email_share():
            sns_publishing.share_quest_by_email(quest, request.user, email_recipients)

    @bgwork.defer
    def alert_followers():
        for follower_id in request.user.redis.new_followers.zrange(0, -1):
            RealtimeChannel('user:{}:rt_tab_badges'.format(follower_id), 1).publish({'tab_badge_update': 'draw'})

    return {
        'quest': quest.details(),
    }

@api('quests_created_by_user')
def ugq_by_user(request, username, offset='top', direction='next'):
    user = get_object_or_404(User, username=username)

    if user.username.lower() == 'questbot':
        quests, pagination = archived_quests(offset=offset)
    else:
        quests, pagination = models.ugq_by_user(user, viewer=request.user)

    return {
        'quests': quests,
        'pagination': pagination,
    }


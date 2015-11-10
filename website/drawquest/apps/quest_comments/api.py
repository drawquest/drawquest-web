from collections import defaultdict, Counter
from datetime import timedelta as td
import math

from cachecow.cache import make_key
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import get_object_or_404

from canvas.cache_patterns import CachedCall
from canvas.exceptions import ServiceError, ValidationError
from canvas.forms import validate_and_clean_comment
from canvas.models import Visibility
from canvas.redis_models import RateLimit, RedisSortedSet
from canvas.util import loads
from canvas import bgwork
from canvas.view_guards import require_user
from drawquest import knobs, economy
from drawquest import sns_publishing
from drawquest.api_cache import cached_api
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quest_comments.details_models import QuestCommentDetails
from drawquest.apps.quest_comments.models import QuestComment, add_viewer_has_starred_field
from drawquest.apps.quest_comments import models
from drawquest.apps.quests.details_models import QuestDetails
from drawquest.apps.quests.models import Quest


urlpatterns = []
api = api_decorator(urlpatterns)


@api('post')
@require_user
def post_quest_comment(request, quest_id, content_id, fact_metadata={},
                       facebook_share=False, facebook_access_token=None,
                       twitter_share=False, twitter_access_token=None, twitter_access_token_secret=None,
                       email_share=False, email_recipients=[],
                       resolve_share_ids=[],
                       uuid=None):
    if not request.user.is_staff and not settings.STAGING:
        prefix = 'user:{}:post_limit:'.format(request.user.id)
        if not RateLimit(prefix+'h', 60, 60*60).allowed() or not RateLimit(prefix+'d', 100, 8*60*60).allowed():
            raise ServiceError("Attempting to post drawings too quickly.")

    _, parent_comment, content, _, _ = validate_and_clean_comment(
        request.user,
        parent_comment=quest_id,
        reply_content=content_id,
    )

    if facebook_share:
        facebook_share = sns_publishing.facebook_share_pre_post(request, facebook_access_token)

    if twitter_share:
        twitter_share = sns_publishing.twitter_share_pre_post(request, twitter_access_token, twitter_access_token_secret)

    comment = QuestComment.create_and_post(request, request.user, content, parent_comment,
                                           uuid=uuid, fact_metadata=fact_metadata, debug_content_id=content_id)

    if facebook_share:
        sns_publishing.facebook_share_post_post(request, facebook_access_token, comment)

    if twitter_share:
        sns_publishing.twitter_share_post_post(request, twitter_access_token, twitter_access_token_secret, comment)

    for share_id in resolve_share_ids:
        share = ShareTrackingUrl.objects.get(id=share_id)

        if share.redirect_url:
            pass #TODO log some error here without failing this request

        share.redirect_url = comment.get_share_page_url()
        share.save()

    if email_share:
        @bgwork.defer
        def defer_email_share():
            sns_publishing.share_comment_by_email(comment, request.user, email_recipients)

    return {
        'comment': comment.details(),
        'balance': economy.balance(request.user),
    }

@api('comment')
def quest_comment(request, comment_id):
    comment = QuestCommentDetails.from_id(comment_id)
    quest = QuestDetails.from_id(comment.quest_id)

    if request.user.is_authenticated():
        comment.user.viewer_is_following = comment.user.id in request.user.following_ids()

    add_viewer_has_starred_field([comment], viewer=request.user)

    return {
        'comment': comment,
        'quest': quest,
    }

def _quest_comments_request_gatekeeper(request, *args, **kwargs):
    if 'force_comment_id' in request.body:
        params = loads(request.body)
        return params.get('force_comment_id') is None

    return True

#DEPRECATED. Use quest_gallery and quest_gallery_for_comment instead.
# Its @api() call is inside drawquest.apps.quests.api
@cached_api(
    timeout=td(days=1),
    namespace='comments',
    key=[
        'quest_comments',
        'v11',
        lambda _, quest_id, **kwargs: quest_id,
    ],
    request_gatekeeper=_quest_comments_request_gatekeeper,
)
def quest_comments(request, quest_id, force_comment_id=None):
    quest = get_object_or_404(Quest, id=quest_id)

    # Exclude curated comments here since we ignore curation status for forced comments, below.
    comments = QuestComment.objects.filter(parent_comment=quest).exclude(visibility=Visibility.CURATED)
    comments = comments.order_by('-id')

    comments = comments[:knobs.COMMENTS_PER_PAGE]
    comments = CachedCall.queryset_details(comments)

    forced_comment = None
    if force_comment_id:
        for comment in comments:
            if str(comment.id) == str(force_comment_id):
                forced_comment = comment
                break

    if force_comment_id and forced_comment is None:
        forced_comment = QuestComment.details_by_id(force_comment_id)()

    if forced_comment is not None and str(forced_comment.id) not in [str(comment.id) for comment in comments]:
        comments.append(forced_comment)

    return {'comments': comments}



_USER_COMMENTS_CACHE_VERSION = 'v15'

# DEPRECATED as of 1.0.3
@api('user_comments')
@cached_api(timeout=td(days=14), key=[
    'user_comments',
    _USER_COMMENTS_CACHE_VERSION,
    lambda request, username, page='top': [username, request.user.username == username, page],
])
def user_comments(request, username, page='top'):
    user = get_object_or_404(User, username=username)
    comments = QuestComment.by_author(user)

    if request.user.id != user.id:
        comments = comments.exclude(visibility=Visibility.CURATED)

    comments = comments[:knobs.COMMENTS_PER_PAGE]
    comments = CachedCall.queryset_details(comments)

    return {
        'comments': comments,
    }

@api('user_comments/v2')
def user_comments_v2(request, username, offset='top', include_reactions=False):
    """
    Includes pagination.
    """
    user = get_object_or_404(User, username=username)
    comments, pagination = models.user_comments(user, request.user, offset=offset, include_ugq=True, include_reactions=include_reactions)

    if request.user.is_authenticated():
        following = request.user.following_ids()

        for comment in comments:
            comment.user.viewer_is_following = comment.user.id in following

    return {
        'comments': comments,
        'pagination': pagination,
    }

@api('user_comments/v3')
def user_comments_v3(request, username, offset='top', include_reactions=False):
    """
    Includes pagination and UGQ.
    """
    user = get_object_or_404(User, username=username)
    comments, pagination = models.user_comments(user, request.user, offset=offset, include_reactions=include_reactions)

    if request.user.is_authenticated():
        following = request.user.following_ids()

        for comment in comments:
            comment.user.viewer_is_following = comment.user.id in following

    return {
        'comments': comments,
        'pagination': pagination,
    }

def invalidate_user_comments(comment):
    #TODO make django-cachecow namespaces dynamic, and then we can key it off the user ID and wipe it all in 
    # one go instead of deleting individual keys.
    author = comment.author
    pages = int(math.ceil(QuestComment.all_objects.filter(author=author).count() / float(knobs.COMMENTS_PER_PAGE)))

    for page in range(1, pages + 1) + ['top', None]:
        for viewer_is_author in [True, False]:
            for endpoint_key in ['user_comments']:
                key_args = [
                    endpoint_key,
                    _USER_COMMENTS_CACHE_VERSION,
                    author.username,
                    viewer_is_author,
                ]
                if page is not None:
                    key_args.append(page)
                key = make_key(key_args)
                cache.delete(key)


@api('rewards_for_posting')
def rewards_for_posting(request, quest_id, facebook=False, tumblr=False, twitter=False):
    rewards = defaultdict(int)

    def reward(name):
        rewards[name] += knobs.REWARDS[name]

    if not request.user.is_authenticated() or QuestComment.posting_in_first_quest(request.user):
        reward('first_quest')

        ret = {'rewards': rewards}

        if request.user.is_authenticated():
            streak, days_to_next_streak, next_streak_goal = QuestComment.posting_would_reward_streak(request.user)

            ret.update({
                'days_to_next_streak': days_to_next_streak,
                'next_streak_goal': next_streak_goal,
            })

        return ret

    quest = get_object_or_404(Quest, id=quest_id)

    if QuestComment.posting_would_complete_quest_of_the_day(request.user, quest):
        reward('quest_of_the_day')
    elif QuestComment.posting_would_complete_archived_quest(request.user, quest):
        reward('archived_quest')

    if QuestComment.posting_in_first_quest(request.user):
        reward('first_quest')

    if facebook:
        reward('personal_share')

    if twitter:
        reward('personal_twitter_share')

    streak, days_to_next_streak, next_streak_goal = QuestComment.posting_would_reward_streak(request.user)
    if streak:
        reward('streak_{}'.format(streak))

    return {
        'rewards': rewards,
        'days_to_next_streak': days_to_next_streak,
        'next_streak_goal': next_streak_goal,
    }

@api('delete')
@require_user
def delete_comment(request, comment_id):
    comment = get_object_or_404(QuestComment.all_objects, id=comment_id)

    if comment.author_id != request.user.id:
        raise ValidationError({
            'comment_id': ["You can't delete a drawing that you didn't author yourself."],
        })

    comment.moderate_and_save(Visibility.UNPUBLISHED, request.user, undoing=True)

@api('viewed')
def viewed_comments(request, comment_ids):
    if not request.user.is_authenticated():
        return
    
    # Rudimentary uniqueness filtering, could be improved with longer-lived record-keeping.
    comment_ids = list(set(comment_ids))

    for comment_id, count in Counter(comment_ids).items():
        RedisSortedSet('quest_comment_views').zincrby(comment_id, count)


# To connect signals.
import drawquest.apps.quest_comments.signals


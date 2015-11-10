from datetime import timedelta as td

from django.shortcuts import get_object_or_404

from drawquest.api_cache import cached_api
from drawquest.api_decorators import api_decorator
from drawquest.apps.explore import models
from drawquest import knobs
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user


urlpatterns = []
api = api_decorator(urlpatterns)


@api('comments')
def explore_comments(request):
    from drawquest.apps.quest_comments.details_models import QuestCommentExploreDetails

    comments = models.explore_comment_details(viewer=request.user)
    comments = models.shuffle_explore_comments(comments)

    if request.user.is_authenticated():
        following = request.user.following_ids()

        for comment in comments:
            comment.user.viewer_is_following = comment.user.id in following

    return {
        'comments': comments,
        'display_size': min(len(comments), knobs.EXPLORE_DISPLAY_SIZE),
    }


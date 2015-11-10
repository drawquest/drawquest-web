from datetime import timedelta as td

from django.db.models.signals import post_save
from django.shortcuts import get_object_or_404
from django.http import Http404

import canvas.signals
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_cache import cached_api
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.gallery import models
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import Quest


urlpatterns = []
api = api_decorator(urlpatterns)


@api('gallery')
def quest_gallery(request, quest_id, offset='top', direction='next', include_reactions=True):
    quest = get_object_or_404(Quest, id=quest_id)
    comments, pagination = models.gallery_comments(quest, offset=offset, direction=direction, viewer=request.user, include_reactions=include_reactions)

    return {
        'comments': comments,
        'pagination': pagination,
        'quest': quest.details(),
    }

@api('top_gallery')
def quest_top_gallery(request, quest_id, include_reactions=True):
    quest = get_object_or_404(Quest, id=quest_id)
    comments = models.top_gallery_comments(quest, viewer=request.user, include_reactions=include_reactions)

    return {
        'comments': comments,
        'quest': quest.details(),
    }

@api('gallery_for_comment')
def quest_gallery_for_comment(request, comment_id, include_reactions=True):
    comment = get_object_or_404(QuestComment, id=comment_id)

    try:
        quest = Quest.objects.get(id=comment.parent_comment_id)
    except Quest.DoesNotExist:
        raise Http404()

    comments, pagination = models.gallery_comments(quest, force_comment=comment, viewer=request.user, include_reactions=include_reactions)

    return {
        'comments': comments,
        'pagination': pagination,
        'quest': quest.details(),
    }

# To connect signals.
import drawquest.apps.gallery.signals


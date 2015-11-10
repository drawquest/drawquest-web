from django.db import models

from canvas.cache_patterns import CachedCall
from canvas.models import Visibility, CommentSticker
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.pagination import Paginator
from drawquest import knobs


def starred_comments_gallery(user, offset='top', direction='next'):
    stars = CommentSticker.objects.filter(user=user).order_by('-timestamp')
    pagination = Paginator(stars, knobs.COMMENTS_PER_PAGE, offset=offset, direction=direction)

    comments = CachedCall.multicall([QuestComment.details_by_id(id_)
                                     for id_
                                     in pagination.items.values_list('comment_id', flat=True)])

    return comments, pagination
    

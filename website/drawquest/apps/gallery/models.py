from datetime import timedelta as td

from cachecow.decorators import cached_function
from django.db import models
from django.http import Http404

from canvas import json
from canvas.cache_patterns import CachedCall
from canvas.models import Visibility
from drawquest import knobs, economy
from drawquest.apps.quest_comments.models import QuestComment, add_viewer_has_starred_field
from drawquest.apps.quest_comments.details_models import QuestCommentGalleryDetails, QuestCommentDetails
from drawquest.apps.quests.models import Quest
from drawquest.pagination import Paginator


def _exclude_flagged(comments, viewer):
    if viewer is not None and viewer.is_authenticated():
        return comments.exclude(flags__user=viewer)

    return comments

def _all_gallery_comments(quest):
    comments = QuestComment.objects.filter(parent_comment=quest).exclude(visibility=Visibility.CURATED)
    return comments.order_by('-id')

def gallery_comments(quest, offset='top', direction='next', force_comment=None, viewer=None,
                     include_reactions=True):
    """
    Returns comments, pagination. Each comment is itself a dict.
    """
    if force_comment is not None:
        newer_comments = QuestComment.objects.filter(parent_comment=quest, id__gt=force_comment.id).order_by('id').values_list('id', flat=True)
        try:
            offset = list(newer_comments[:knobs.COMMENTS_PER_PAGE / 2])[-1]
        except IndexError:
            offset = force_comment.id

    pagination = Paginator(_exclude_flagged(_all_gallery_comments(quest), viewer), knobs.COMMENTS_PER_PAGE, offset=offset, direction=direction)

    comments = pagination.items

    promoter = None if include_reactions else QuestCommentGalleryDetails
    comments = CachedCall.queryset_details(comments, promoter=promoter)

    add_viewer_has_starred_field(comments, viewer=viewer)

    if force_comment is not None and force_comment.id not in [cmt['id'] for cmt in comments]:
        if force_comment.visibility != Visibility.CURATED:
            raise Http404()

        comments.append(force_comment.details())
        comments = sorted(comments, key=lambda cmt: -cmt['id'])

    if viewer is not None and viewer.is_authenticated():
        following = viewer.following_ids()

        for comment in comments:
            comment.user.viewer_is_following = comment.user.id in following

    return comments, pagination

@cached_function(
    timeout=td(minutes=15),
    key=['quest_top_gallery_ids', 'v1',
         lambda quest: quest.id],
)
def top_gallery_comment_ids(quest):
    comments = _all_gallery_comments(quest).order_by('-star_count',)
    comment_ids = comments.values_list('id', flat=True)
    comment_ids = comment_ids[:knobs.TOP_GALLERY_SIZE]
    return list(comment_ids)

def top_gallery_comments(quest, viewer=None, include_reactions=False):
    comment_ids = top_gallery_comment_ids(quest)

    comments = QuestComment.objects.filter(id__in=comment_ids).order_by('-star_count')
    comments = _exclude_flagged(comments, viewer)

    promoter = None if include_reactions else QuestCommentGalleryDetails
    comments = CachedCall.queryset_details(comments, promoter=promoter)

    add_viewer_has_starred_field(comments, viewer=viewer)

    if viewer is not None and viewer.is_authenticated():
        following = viewer.following_ids()

        for comment in comments:
            comment.user.viewer_is_following = comment.user.id in following

    return comments


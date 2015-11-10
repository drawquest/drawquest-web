from datetime import datetime, timedelta
import random
import time

from cachecow.decorators import cached_function
from django.db import models

from canvas.cache_patterns import CachedCall
from canvas.redis_models import redis
from canvas.models import Visibility
from drawquest import knobs
from drawquest.apps.quest_comments.details_models import QuestCommentExploreDetails
from drawquest.apps.quest_comments.models import QuestComment, add_viewer_has_starred_field


def explore_comments_cache_key(prefix=''):
    # year, month, day, hour
    return [prefix, 'explore_comments', 'v9'] + list(last_rollover_datetime().timetuple())[:4]

def _remove_duplicate_authors(comments):
    comments = comments.order_by('-star_count')
    author_ids = set()
    exclude_ids = set()

    for cmt_id, author_id in comments.values_list('id', 'author_id'):
        if author_id in author_ids:
            exclude_ids.add(cmt_id)
        else:
            author_ids.add(author_id)

    return comments.exclude(id__in=exclude_ids)

def last_rollover_datetime():
    rollover_ts = datetime.utcnow() - timedelta(hours=knobs.EXPLORE_ROLLOVER_HOUR)
    return rollover_ts.replace(hour=5, minute=0, second=0, microsecond=0)

def explore_comments():
    follower_cutoffs = [None, 250, 50, 15]
    comment_ids = set()

    rollover_ts_upper = time.mktime(last_rollover_datetime().timetuple())
    rollover_ts_lower = rollover_ts_upper - 60*60*24

    for follower_cutoff in follower_cutoffs:
        comments = QuestComment.objects.filter(visibility=Visibility.PUBLIC,
                                               timestamp__gt=rollover_ts_lower,
                                               timestamp__lt=rollover_ts_upper)

        if follower_cutoff is not None:
            comments = comments.filter(author__userinfo__follower_count__lte=follower_cutoff)

        comments = comments.order_by('-star_count')[:knobs.EXPLORE_BUCKET_SIZE].values_list('id', flat=True)
        comment_ids.update(comments)

    comments = QuestComment.objects.filter(id__in=comment_ids).order_by('-star_count')
    comments = _remove_duplicate_authors(comments)
    return comments

@cached_function(timeout=timedelta(hours=25), key=lambda: explore_comments_cache_key(prefix='ids'))
def explore_comment_ids():
    #return [int(id_) for id_ in redis.zmembers('explore_ids')]
    return list(explore_comments().values_list('id', flat=True))

def preload_explore_comment_ids():
    redis.delete('explore_comment_ids_temp')

    ids = explore_comment_ids()

    for id_ in ids:
        redis.sadd('explore_comment_ids_temp', id_)

    if ids:
        redis.rename('explore_comment_ids_temp', 'explore_comment_ids')

def preloaded_explore_comment_ids():
    return [int(id_) for id_ in redis.smembers('explore_comment_ids')] or []

def explore_comment_details(viewer=None):
    comments = CachedCall.multicall([QuestComment.details_by_id(id_, promoter=QuestCommentExploreDetails) for id_ in preloaded_explore_comment_ids()])

    add_viewer_has_starred_field(comments, viewer=viewer)

    return comments

def shuffle_explore_comments(comments):
    if not comments:
        return comments

    comments = sorted(comments, key=lambda cmt: -cmt.star_count)
    first = random.choice(comments[:len(comments) / 4])
    comments = [cmt for cmt in comments if cmt.id != first.id]
    random.shuffle(comments)

    return [first] + comments


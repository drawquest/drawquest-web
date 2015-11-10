from collections import OrderedDict
from functools import partial
import itertools

from canvas.redis_models import redis, RedisLastBumpedBuffer
from drawquest import knobs
from drawquest.apps.quest_comments.details_models import QuestCommentGalleryDetails
from drawquest.pagination import FakePaginator


class _KeyedFeedBufferBase(RedisLastBumpedBuffer):
    def __init__(self, key_id, size):
        key = self.get_key(key_id)
        super(_KeyedFeedBufferBase, self).__init__(key, size, getter=self._GETTER)

    @classmethod
    def get_key(cls, key_id):
        return cls._KEY.format(key_id)

    def __contains__(self, member):
        return redis.zrank(self.key, member) is not None


class UserFeedSourceBuffer(_KeyedFeedBufferBase):
    """ Holds Comment IDs. """
    _KEY = 'user:{}:feed_source'
    _GETTER = int

    def bump(self, comment):
        """
        Takes a Comment or QuestCommentDetails instance.

        Will safely reject comments that aren't visible in the feed.
        """
        if hasattr(comment, 'details'):
            comment = comment.details()

        item = {
            'type': 'comment',
            'comment': comment,
        }

        if not visible_in_feed(item):
            return

        super(UserFeedSourceBuffer, self).bump(comment.id)


def _tighten_earliest_timestamp_cutoff(earliest_timestamp_cutoff):
    """ Ugly hack for float precision. """
    if earliest_timestamp_cutoff is None:
        return

    if isinstance(earliest_timestamp_cutoff, basestring):
        earliest_timestamp_cutoff = earliest_timestamp_cutoff.strip("'")

    return float(earliest_timestamp_cutoff) - 0.00001

def visible_in_feed(item, earliest_timestamp_cutoff=None):
    comment = item['comment']

    try:
        if float(item['ts']) > float(earliest_timestamp_cutoff):
            return False
    except (KeyError, TypeError,):
        pass

    return comment.is_visible()


def not_self_authored(item, username=None):
    return username != item['comment'].user.username

def _feed_items(user, earliest_timestamp_cutoff=None, items_to_skip=set()):
    feed_source_keys = [UserFeedSourceBuffer.get_key(user_id)
                        for user_id in user.redis.new_following.zrange(0, -1)]

    max_score = _tighten_earliest_timestamp_cutoff(earliest_timestamp_cutoff)

    comments = [{'type': 'comment', 'comment_id': id_, 'ts': score}
                for id_, score
                in redis.zunion(feed_source_keys,
                                withscores=True, transaction=False, max_score=max_score)]

    # Sort by recency.
    items = sorted(itertools.chain(comments), key=lambda e: float(e['ts']), reverse=True)

    # Skip items as requested and skip comments the user has hidden.
    comments_to_skip = set(str(item['comment_id']) for item in items_to_skip)
    comments_to_skip |= set(user.flags.all().values_list('id', flat=True))

    # Remove dupes.
    items = OrderedDict((str(item['comment_id']), item,) for item in items
                        if str(item['comment_id']) not in comments_to_skip).values()

    return items

def feed_for_user(user, offset='top', direction='next', items_to_skip=set(), viewer=None):
    from drawquest.apps.quest_comments.models import add_viewer_has_starred_field

    if direction != 'next':
        raise ValueError("Feed only supports 'next' direction, i.e. scrolling in one direction.")

    earliest_timestamp_cutoff = None if offset == 'top' else offset

    items = _feed_items(user, earliest_timestamp_cutoff=earliest_timestamp_cutoff, items_to_skip=items_to_skip)

    # Pagination.
    items = items[:knobs.COMMENTS_PER_PAGE]
    try:
        next_offset = items[-1]['ts']
        next_offset = '{:.18}'.format(next_offset)
    except IndexError:
        next_offset = None
    pagination = FakePaginator(items, offset=offset, next_offset=next_offset)

    details = QuestCommentGalleryDetails.from_ids([item['comment_id'] for item in items])
    add_viewer_has_starred_field(details, viewer=viewer)
    details_by_id = dict((cmt.id, cmt) for cmt in details)
    items = [item for item in items if int(item['comment_id']) in details_by_id]
    for item in items:
        item['comment'] = details_by_id[int(item['comment_id'])]

    # Prune items that shouldn't show up in this feed.
    items = filter(partial(visible_in_feed, earliest_timestamp_cutoff=earliest_timestamp_cutoff), items)
    items = filter(partial(not_self_authored, username=user.username), items)

    return items, pagination

def _filter_comments(items):
    return [item.get('comment', item['comment_id']) for item in items if item['type'] == 'comment']

def feed_comments_for_user(*args, **kwargs):
    items, pagination = feed_for_user(*args, **kwargs)
    return _filter_comments(items), pagination

def has_new_feed_comments(user, since_timestamp):
    items = _feed_items(user, earliest_timestamp_cutoff=since_timestamp)

    if not items:
        return False

    return any(float(item['ts']) > since_timestamp for item in items if item['type'] == 'comment')


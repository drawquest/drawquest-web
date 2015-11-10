from datetime import date
import itertools

from django.db.models import *
from django.conf import settings

from apps.canvas_auth.models import User
from canvas import util, knobs
from canvas.cache_patterns import CachedCall
from canvas.exceptions import ResponseTooLarge
from canvas.models import BaseCanvasModel, Category
from canvas.util import UnixTimestampField, Now
from drawquest.apps.drawquest_auth.details_models import UserDetails


ACTIVITY_TYPE_IDS = {
    'sticker':          0,
    'epic_sticker':     1,
    'level_up':         2,
    'followed_by_user': 3,
    'remix_invite':     4,
    'thread_promoted':  5,
    'post_promoted':    6,
    'remix_invite_monster': 7,
    'thread_reply':     8,
    'remix':            9,
    'reply':            10,
    'daily_free_stickers': 11,
    'welcome':          12,
    'starred':          13,
    'playback':         14,
    'featured_in_explore': 15,
    'followee_posted':  16,
    'facebook_friend_joined': 17,
    'twitter_friend_joined': 18,
    'email_frien_joined': 19,
    'new_color_alert':  20,
    'followee_created_ugq':  21,
    '__example__':      9001,
}


def activity_stream_items(user, later_than=None, earlier_than=None, iphone=False):
    if iphone:
        stream = user.redis.iphone_activity_stream
    else:
        stream = user.redis.activity_stream

    count = knobs.ACTIVITY_STREAM_PER_PAGE

    if earlier_than is not None and later_than is not None:
        raise ValueError("Can't specify both later_than and earlier_than.")

    if earlier_than is not None:
        activities = stream.earlier_than(earlier_than, num=count)
    elif later_than is not None:
        activities = stream.later_than(later_than, num=(count + 1))

        if len(activities) > count:
            raise ResponseTooLarge("Too many items returned in the requested range.")

        activities = activities[:count]
    else:
        activities = list(stream[:count])

    return activities


class Activity(BaseCanvasModel):
    actor_id = BigIntegerField(blank=True, null=True)
    timestamp = UnixTimestampField()
    activity_type = IntegerField(blank=False)
    data = TextField()
    key = BigIntegerField(blank=True, null=True)

    # Common fields, better to have in SQL than JSON.
    comment_id = BigIntegerField(blank=True, null=True)
    quest_id = BigIntegerField(blank=True, null=True)

    class Meta(object):
        unique_together = ('activity_type', 'key')

    @classmethod
    def from_redis_activity(cls, activity, key=None):
        act = cls()

        activity_data = activity.to_dict()

        if activity.actor:
            act.actor_id = int(activity.actor['id'])

        act.quest_id = activity_data.get('quest_id')
        act.comment_id = activity_data.get('comment_id')

        act.timestamp = activity.timestamp
        act.activity_type = ACTIVITY_TYPE_IDS[activity.TYPE]
        act.key = key
        discard_keys = ['actor', 'ts', 'type', 'quest_id', 'comment_id']
        act._data = {k: activity_data[k] for k in activity_data.keys() if k not in discard_keys}
        act.data = util.dumps(act._data)
        act.save()

        return act

    def _details(self):
        base = util.loads(self.data)
        base.update({
            'id': self.id,
            'ts': self.timestamp,
            'activity_type': dict((v, k) for k, v in ACTIVITY_TYPE_IDS.items())[self.activity_type],
        })

        if self.quest_id:
            base['quest_id'] = self.quest_id

        if self.comment_id:
            base['comment_id'] = self.comment_id

        #TODO have a UserDetails for example.com too to get rid of this branch.
        if self.actor_id:
            base['actor'] = UserDetails.from_id(self.actor_id).to_client()

        return base

    @classmethod
    def details_by_id(cls, id, **kwargs):
        return CachedCall(
            'activity:{}:details_v3'.format(id),
            lambda: cls.objects.get(id=id)._details(),
            10*24*60*60,
        )

    @property
    def details(self):
        return self.details_by_id(self.id)


# Deprecated.
class LegacyActivity(BaseCanvasModel):
    actor = ForeignKey(User, null=True)
    timestamp = UnixTimestampField()
    activity_type = CharField(max_length=40, blank=False)
    data = TextField()
    key = PositiveIntegerField(blank=True, null=True)

    class Meta(object):
        db_table = 'activity_legacyactivity'

    @classmethod
    def from_redis_activity(cls, activity, key=None):
        act = cls()

        if activity.actor:
            act.actor_id = int(activity.actor['id'])

        act.timestamp = activity.timestamp
        act.activity_type = activity.TYPE
        act.key = key
        discard_keys = ['actor', 'ts', 'type']
        base = activity.to_dict()
        act._data = {k: base[k] for k in base.keys() if k not in discard_keys}
        act.data = util.dumps(act._data)
        act.save()

        return act

    def _details(self):
        base = util.loads(self.data)
        base.update({
            'id': self.id,
            'ts': self.timestamp,
            'activity_type': self.activity_type,
        })

        #TODO have a UserDetails for example.com too to get rid of this branch.
        if self.actor_id:
            base['actor'] = UserDetails.from_id(self.actor_id).to_client()

        return base

    @classmethod
    def details_by_id(cls, id, **kwargs):
        return CachedCall(
            "activity:%s:details_v2" % id,
            lambda: cls.objects.get(id=id)._details(),
            30*24*60*60,
        )

    @property
    def details(self):
        return self.details_by_id(self.id)


def legacy_get_activity_stream_items(user, earliest_timestamp_cutoff=None, count=knobs.ACTIVITY_STREAM_PER_PAGE):
    stream = user.redis.activity_stream

    #TODO This is broken but example.com uses it..?
    if earliest_timestamp_cutoff:
        stream = stream.earlier_than(earliest_timestamp_cutoff)

    return list(stream[:count])


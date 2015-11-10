from collections import OrderedDict

from datetime import timedelta as td

from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from cachecow.decorators import cached_function
from django.utils.translation import ugettext, ugettext_lazy as _, pgettext, pgettext_lazy
from django.conf import settings
from django.db.models import *
from django.db.models.signals import post_save

from canvas import bgwork, util
from canvas.cache_patterns import CachedCall
from canvas.models import BaseCanvasModel, Comment, Content, get_mapping_id_from_short_id, Visibility
from canvas.redis_models import redis, RealtimeChannel, RedisSortedSet
from canvas.util import UnixTimestampField
from canvas.notifications.actions import Actions
from drawquest import knobs
from drawquest.apps.drawquest_auth.models import User, AnonymousUser
from drawquest.apps.push_notifications.models import push_notification
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests import signals
from drawquest.pagination import Paginator
from drawquest.apps.quest_invites.models import InvitedQuests
from drawquest.apps.quests.top import top_quests_buffer, get_quest_score
from services import Services


class ScheduledQuest(BaseCanvasModel):
    quest = ForeignKey('Quest', null=False)
    curator = ForeignKey(User, blank=True, null=True, default=None, related_name='scheduled_quests')
    timestamp = UnixTimestampField(default=0)
    appeared_on = UnixTimestampField(null=True, db_index=True)
    sort = IntegerField()

    class Meta:
        ordering = ['-appeared_on']

    @classmethod
    def get_or_create(cls, quest):
        if quest.parent_comment_id:
            quest = quest.parent_comment

        try:
            return cls.objects.get(quest=quest.id)
        except cls.DoesNotExist:
            return cls.objects.create(quest=Quest.objects.get(pk=quest.id), sort=1)

    @classmethod
    def archived(cls, select_quests=False):
        qs = cls.objects
        if select_quests:
            qs = qs.select_related('quest')

        current_quest_id = redis.get('dq:current_scheduled_quest')
        if current_quest_id:
            qs = qs.exclude(id=current_quest_id)

        return qs.exclude(appeared_on__isnull=True).order_by('-appeared_on')

    @classmethod
    def unarchived(cls):
        return cls.objects.filter(appeared_on__isnull=True).order_by('sort')

    def _publish_quest_of_the_day(self):
        signals.current_quest_changed.send(ScheduledQuest, instance=self)

        RealtimeChannel('qotd', 1).publish({'quest_id': self.quest_id})

        push_notification('quest_of_the_day',
                          _(u"Today's Quest: %(quest_title)s" % {'quest_title': self.quest.title}),
                          extra_metadata={'quest_id': self.quest.id},
                          badge=1)

    def set_as_current_quest(self):
        redis.set('dq:current_scheduled_quest', self.id)
        self.appeared_on = Services.time.time()
        self.save()
        self.quest.details.force()
        self._publish_quest_of_the_day()

    @classmethod
    def rollover_next_quest(cls):
        """ Sets the next scheduled quest as the currently active one / quest of the day. """
        try:
            cls.unarchived().order_by('sort')[0].set_as_current_quest()
        except IndexError:
            cls.archived().exclude(quest__title='Give him a smile!').order_by('appeared_on')[0].set_as_current_quest()

    @classmethod
    def current_scheduled_quest(cls):
        """ The `ScheduledQuest` instance representing the current quest of the day. """
        scheduled_quest_id = redis.get('dq:current_scheduled_quest')
        if scheduled_quest_id:
            return cls.objects.get(id=scheduled_quest_id)


class QuestManager(Visibility.PublicOnlyManager):
    def get_query_set(self):
        return super(QuestManager, self).get_query_set().filter(parent_comment__isnull=True)


class QuestAllManager(Manager):
    def get_query_set(self):
        return super(QuestAllManager, self).get_query_set().filter(parent_comment__isnull=True)

class QuestPublishedManager(Visibility.PublishedOnlyManager):
    def get_query_set(self):
        return super(QuestPublishedManager, self).get_query_set().filter(parent_comment__isnull=True)

class QuestVisibleOnlyManager(Visibility.PublishedOnlyManager):
    def get_query_set(self):
        return super(QuestVisibleOnlyManager, self).get_query_set().filter(parent_comment__isnull=True)


class Quest(Comment):
    objects = QuestManager()
    all_objects = QuestAllManager()
    published = QuestPublishedManager()
    visible = QuestVisibleOnlyManager()

    class Meta:
        proxy = True

    @property
    def comments_url(self):
        return settings.API_PREFIX + 'quests/comments'

    @property
    def comments(self):
        return self.replies

    @classmethod
    def completed_by_user_count(self, user):
        """ The number of quests a user has completed. """
        return QuestComment.by_author(user).values('parent_comment_id').distinct().count()

    def first_appeared_on(self):
        if self.ugq:
            return self.timestamp

        if self.scheduledquest_set.exists():
            return self.scheduledquest_set.all()[0].appeared_on

    def get_absolute_url(self):
        if not slugify(self.title):
            return '/q/' + util.base36encode(self.id)

        return reverse('quest', args=[util.base36encode(self.id), slugify(self.title)])

    def author_count(self):
        return self.replies.values_list('author_id', flat=True).distinct().count()

    def drawing_count(self):
        return self.replies.exclude(reply_content__isnull=True).count()

    def schedule(self, ordinal, curator=None):
        """ Returns `scheduled_quest` instance. """
        scheduled_quest = ScheduledQuest.get_or_create(self)

        if not scheduled_quest.curator:
            scheduled_quest.curator = curator
            scheduled_quest.timestamp = Services.time.time()

        scheduled_quest.sort = ordinal
        scheduled_quest.save()
        return scheduled_quest

    def is_currently_scheduled(self):
        """ 'currently scheduled' means it's the quest of the day. """
        scheduled_quest = ScheduledQuest.objects.get(id=redis.get('dq:current_scheduled_quest'))
        return scheduled_quest.quest_id == self.id

    def is_onboarding_quest(self):
        return str(knobs.ONBOARDING_QUEST_ID) == str(self.id)

    def user_has_completed(self, user):
        """ Whether `user` has contributed a drawing for this quest. """
        return self.replies.filter(author=user).exclude(reply_content__isnull=True).exists()

    def attribute_to_user(self, user, attribution_copy):
        self.attribution_user = user
        self.attribution_copy = attribution_copy
        self.save()
        self.details.force()

    def clear_attribution(self):
        self.attribution_user = None
        self.attribution_copy = ''
        self.save()
        self.details.force()

    def dismiss(self, dismisser):
        dismisser.redis.dismissed_quests.dismiss_quest(self)

    def update_score(self):
        score = get_quest_score(self)
        top_quests_buffer.bump(self.id, score)
        return score

    @property
    def invited_users(self):
        from drawquest.apps.quest_invites.models import InvitedUsers

        return InvitedUsers(self)

    def _details(self):
        content_details = self.reply_content.details().to_backend() if self.reply_content else {}

        ts = self.timestamp
        if self.scheduledquest_set.exists():
            ts = self.scheduledquest_set.all().order_by('-appeared_on')[0].appeared_on or ts

        ret = {
            'id': self.id,
            'author_id': self.author_id,
            'content': content_details,
            'timestamp': ts,
            'title': self.title,
            'comments_url': self.comments_url,
            'author_count': self.author_count(),
            'drawing_count': self.drawing_count(),
            'visibility': self.visibility,
            'attribution_copy': self.attribution_copy,
            'ugq': self.ugq,
        }

        try:
            ret['attribution_username'] = self.attribution_user.username
            user = User.objects.get(id=self.attribution_user_id)

            if user.userinfo.avatar:
                ret['attribution_avatar_url'] = user.userinfo.avatar.details().get_absolute_url_for_image_type('archive')

            ret['attribution_avatar_urls'] = user.details().avatar_urls['gallery']
        except AttributeError:
            ret['attribution_username'] = None

        return ret

    @classmethod
    def details_by_id(cls, quest_id, promoter=None):
        from drawquest.apps.quests.details_models import QuestDetails

        if promoter is None:
            promoter = QuestDetails

        def inner_call():
            return cls.all_objects.get(id=quest_id)._details()

        return CachedCall(
            'quest:{}:details_v15'.format(quest_id),
            inner_call,
            24*60*60,
            promoter=promoter,
        )

    @property
    def details(self):
        return self.details_by_id(self.id)

    @classmethod
    def _auto_moderation(cls, author):
        """ Returns (skip_moderation, curate,) booleans. """
        curate = ((author.userinfo.trusted is None and redis.get('dq:auto_curate'))
                  or author.userinfo.trusted == False)

        return False, curate

    @classmethod
    def create_and_post(cls, request, author, title, content=None, ugq=False):
        skip_moderation, curate = cls._auto_moderation(author)

        quest = super(Quest, cls).create_and_post(
            request,
            author,
            False,
            None,
            content,
            curate=curate,
            skip_moderation=skip_moderation,
            ugq=ugq,
            title=title,
        )

        if ugq:
            author.redis.ugq_buffer.bump(quest.id)

            @bgwork.defer
            def followee_created_ugq():
                Actions.followee_created_ugq(author, quest)

        return quest

    def get_share_page_url(self, absolute=False):
        slug = slugify(self.title)

        if slug:
            url = reverse('quest', args=[util.base36encode(self.id), slug])
        else:
            url = '/q/{}'.format(util.base36encode(self.id))

        if absolute:
            url = 'http://' + settings.DOMAIN + url

        return url


class DismissedQuests(RedisSortedSet):
    def __init__(self, user):
        self.user_id = getattr(user, 'id', user)

        super(DismissedQuests, self).__init__('user:{}:dismissed_quests'.format(self.user_id))

    def dismiss_quest(self, quest):
        """ `comment` can be a Comment or CommentDetails. """
        self.zadd(quest.id, Services.time.time())

    def filter_quests(self, quests):
        hidden_quest_ids = set(int(id_) for id_ in self.zrange(0, -1))

        return [quest for quest in quests if int(quest.id) not in hidden_quest_ids]


def _dedupe_quests(quests):
    ''' Each quest should be a dict with id and timestamp. Favors recency. '''
    quests = sorted(quests, key=lambda quest: quest['timestamp'])
    quests = dict((cmt['id'], cmt['timestamp']) for cmt in quests)
    quests = [{'id': id_, 'timestamp': timestamp} for id_, timestamp in quests.items()]
    return quests


@cached_function(timeout=td(days=30), key=[
    'completed_quest_ids_with_timestamps', 'v5',
    lambda user: getattr(user, 'id', user),
])
def completed_quest_ids_with_timestamps(user):
    from drawquest.apps.quest_comments.models import QuestComment

    user_id = getattr(user, 'id', user)

    comments = QuestComment.objects.filter(author_id=user_id).exclude(reply_content__isnull=True).values('parent_comment_id', 'timestamp')
    quests = [{'id': cmt['parent_comment_id'], 'timestamp': cmt['timestamp']}
              for cmt in comments]
    quests = _dedupe_quests(quests)
    quests = list(sorted(quests, key=lambda cmt: cmt['timestamp']))

    return quests

# Cache invalidation for completed_quest_ids.
post_save.connect(
    lambda sender, instance, **kwargs: completed_quest_ids_with_timestamps.delete_cache(instance.author_id),
    sender=QuestComment, dispatch_uid='post_save_for_completed_quest_ids_with_timestamps_api', weak=False
)


def completed_quest_ids(user):
    quests = completed_quest_ids_with_timestamps(user)
    quests = sorted(quests, key=lambda quest: quest['timestamp'])
    return [quest['id'] for quest in quests]

def archived_quests(offset=None):
    """ Returns quest details. """
    def get_cached(archived_quests):
        return CachedCall.multicall([archived.quest.details for archived in archived_quests])

    archived_quests = ScheduledQuest.archived(select_quests=True)

    if offset is None:
        return get_cached(archived_quests)

    pagination = Paginator(archived_quests, knobs.QUESTS_PER_PAGE, offset=offset)
    archived_quests = pagination.items
    archived_quests = get_cached(archived_quests)

    return archived_quests, pagination

def current_quest_details():
    try:
        quest = ScheduledQuest.current_scheduled_quest().quest
    except AttributeError:
        return None

    return quest.details()

def _followee_quest_ids(user, since_timestamp=None):
    buffer_keys = ['ugq_by_user:{}'.format(followee_id)
                   for followee_id in user.redis.new_following.zrange(0, -1)]

    items = redis.zunion(buffer_keys, withscores=True, transaction=False)

    if since_timestamp is not None:
        items = [item for item in items if item[1] > since_timestamp]

    items = sorted(items, key=lambda item: -item[1])
    return [int(item[0]) for item in items]

def _current_quest_for_inbox(user):
    try:
        current_quest = ScheduledQuest.current_scheduled_quest().quest
        if current_quest.replies.filter(author=user).exists():
            return None
        else:
            return current_quest.details()
    except AttributeError:
        return None

def quest_inbox(user):
    """
    Returns quest details in a tuple: current_quest, quests.
    current_quest may be None.
    """
    from drawquest.apps.quests.details_models import QuestDetails

    if not user.is_authenticated():
        return (current_quest_details(), [])

    current_quest = _current_quest_for_inbox(user)

    user_completed_quest_ids = completed_quest_ids(user)

    followee_quest_ids = _followee_quest_ids(user)
    followee_quest_ids = [id_ for id_ in followee_quest_ids
                          if id_ not in user_completed_quest_ids]

    followee_quests = QuestDetails.from_ids(followee_quest_ids[:knobs.QUEST_INBOX_SIZE])
    followee_quests = [(quest, quest.timestamp) for quest in followee_quests]

    invited_quests = user.redis.quest_invites.uncompleted_invites()
    invited_quests = [
        (quest, ts)
        for quest, ts in invited_quests
        if ((current_quest is None or quest.id != current_quest.id)
            and quest.id not in followee_quest_ids)
    ]

    quests = followee_quests + invited_quests
    quests = [(quest, ts) for quest, ts in quests
              if int(quest.id) not in user_completed_quest_ids]
    quests = [quest for quest, ts in sorted(quests, key=lambda q: -q[1])]
    quests = user.redis.dismissed_quests.filter_quests(quests)
    quests = quests[:knobs.QUEST_INBOX_SIZE]

    if (current_quest is not None 
        and (current_quest.id in user_completed_quest_ids
             or str(current_quest.id) in user.redis.dismissed_quests)):
        current_quest = None

    return current_quest, quests

def has_new_inbox_items(user, since_timestamp):
    since_timestamp = int(since_timestamp)

    if _current_quest_for_inbox(user) is not None:
        return True

    user_completed_quest_ids = completed_quest_ids(user)

    followee_quest_ids = _followee_quest_ids(user, since_timestamp=since_timestamp)
    if any(id_ for id_ in followee_quest_ids if id_ not in user_completed_quest_ids):
        return True

    invited_quests = user.redis.quest_invites.uncompleted_invites()
    if any(ts > since_timestamp for quest, ts in invited_quests):
        return True

    return False

def quest_history(user):
    """ Returns quest details. """
    from drawquest.apps.quests.details_models import QuestDetails

    if not user.is_authenticated():
        return []

    completed_quests = completed_quest_ids_with_timestamps(user)
    completed_quests = sorted(completed_quests, key=lambda q: -q['timestamp'])
    completed_quests = completed_quests[:knobs.QUEST_HISTORY_SIZE]

    ugq = Quest.objects.filter(author=user).order_by('-id').values('id', 'timestamp')
    ugq = list(ugq[:knobs.QUEST_HISTORY_SIZE])

    dismissed_quests = user.redis.dismissed_quests.zrevrange(0, knobs.QUEST_HISTORY_SIZE,
                                                             withscores=True)
    dismissed_quests = [{'id': int(item[0]), 'timestamp': item[1]}
                        for item in dismissed_quests]

    history = completed_quests + ugq + dismissed_quests
    history = _dedupe_quests(history)
    history = sorted(history, key=lambda quest: -quest['timestamp'])
    history = history[:knobs.QUEST_HISTORY_SIZE]
    history = [quest['id'] for quest in history]

    return QuestDetails.from_ids(history)


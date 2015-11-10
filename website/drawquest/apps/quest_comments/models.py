import datetime
import itertools

from django.conf import settings
from django.db.models import *

from canvas import bgwork, util
from canvas.signals import visibility_changed as visibility_changed_signal
from canvas.cache_patterns import CachedCall
from canvas.models import BaseCanvasModel, Comment, Content, CommentSticker, Visibility
from canvas.notifications.actions import Actions
from canvas.redis_models import redis, RealtimeChannel
from drawquest import economy, knobs
from drawquest.apps.quest_comments.details_models import QuestCommentGalleryDetails
from drawquest.apps.drawquest_auth.details_models import UserDetails
from drawquest.pagination import Paginator
from drawquest.apps.drawquest_auth.models import User, AnonymousUser
from services import Services
from website.apps.share_tracking.models import ShareTrackingUrl


class QuestCommentManager(Visibility.PublicOnlyManager):
    def get_query_set(self):
        return super(QuestCommentManager, self).get_query_set().filter(parent_comment__isnull=False)


class QuestCommentAllManager(Manager):
    def get_query_set(self):
        return super(QuestCommentAllManager, self).get_query_set().filter(parent_comment__isnull=False)


class QuestCommentPublishedManager(Visibility.PublishedOnlyManager):
    def get_query_set(self):
        return super(QuestCommentPublishedManager, self).get_query_set().filter(parent_comment__isnull=False)


class QuestCommentVisibleOnlyManager(Visibility.PublishedOnlyManager):
    def get_query_set(self):
        return super(QuestCommentVisibleOnlyManager, self).get_query_set().filter(parent_comment__isnull=False)


class QuestComment(Comment):
    objects = QuestCommentManager()
    all_objects = QuestCommentAllManager()
    published = QuestCommentPublishedManager()
    visible = QuestCommentVisibleOnlyManager()

    class Meta(object):
        proxy = True

    @classmethod
    def posting_would_complete_quest_of_the_day(cls, author, quest):
        if not author.is_authenticated():
            return quest.is_currently_scheduled()

        return quest.is_currently_scheduled() and not quest.user_has_completed(author)

    @classmethod
    def posting_would_complete_archived_quest(cls, author, quest):
        if quest.ugq:
            return False

        if not author.is_authenticated():
            return not quest.is_currently_scheduled()

        return not quest.is_currently_scheduled() and not quest.user_has_completed(author)

    @classmethod
    def posting_would_reward_streak(cls, author):
        '''
        Returns (current_streak_goal, days_to_next_streak_goal, next_streak_goal).
        If current_streak_goal is None, it means it's not yet at a streak goal.
        '''
        from drawquest.apps.quests.models import ScheduledQuest

        is_streak = False

        STREAKS = [3, 10, 100]

        comments = QuestComment.all_objects.filter(author=author)
        comments = comments.filter(timestamp__gte=(Services.time.time()
                                                   - ((STREAKS[-1] + 2) * 60*60*24)))

        def to_day(ts):
            if ts.hour >= 16:
                return ts.date() 
            else:
                return ts.date() - datetime.timedelta(days=1)

        timestamps = comments.values_list('timestamp', flat=True)
        timestamps = [datetime.datetime.utcfromtimestamp(ts) for ts in timestamps]
        dates = set(to_day(ts) for ts in timestamps)

        today = to_day(Services.time.utcnow())
        new_streak_today = today not in dates
        streak = 1
        dates.add(today)
        dates = list(reversed(sorted(dates)))

        for later_date, date in zip(dates, dates[1:]):
            if later_date - datetime.timedelta(days=1) != date:
                break

            streak += 1

        try:
            next_streak_goal = [d for d in STREAKS if d > streak][0]
        except IndexError:
            next_streak_goal = None

        if streak > STREAKS[-1] or (not new_streak_today and next_streak_goal is None):
            return None, None, None
        elif not new_streak_today:
            return None, next_streak_goal - streak, next_streak_goal
        elif streak == STREAKS[-1]:
            return STREAKS[-1], 0, None

        if streak in STREAKS:
            return streak, 0, next_streak_goal

        return None, next_streak_goal - streak, next_streak_goal

    @classmethod
    def posting_in_first_quest(cls, author):
        return not author.comments.exists()

    @classmethod
    def _auto_moderation(cls, author):
        """ Returns (skip_moderation, curate,) booleans. """
        if not author.comments.exists():
            return True, True

        last_drawing = None
        if author.comments.exists():
            last_drawing = author.comments.order_by('-id')[0]

        if (last_drawing
                and last_drawing.stickers.filter(type_id=settings.STAR_STICKER_TYPE_ID).count()
                    > knobs.AUTO_MODERATION['stars']):
            return True, False

        curate = ((author.userinfo.trusted is None and redis.get('dq:auto_curate'))
                  or author.userinfo.trusted == False)
        return False, curate

    @classmethod
    def create_and_post(cls, request, author, content, quest, uuid=None, fact_metadata=None, debug_content_id=None):
        from drawquest.apps.quests.models import Quest

        if not isinstance(quest, Quest):
            quest = Quest.objects.get(id=quest.id)

        was_first_quest = QuestComment.posting_in_first_quest(request.user)
        was_quest_of_the_day = cls.posting_would_complete_quest_of_the_day(author, quest)
        was_archived_quest = cls.posting_would_complete_archived_quest(author, quest)

        skip_moderation, curate = cls._auto_moderation(author)

        comment = super(QuestComment, cls).create_and_post(
            request,
            author,
            False,
            None,
            content,
            parent_comment=quest,
            fact_metadata=fact_metadata,
            posted_on_quest_of_the_day=quest.is_currently_scheduled(),
            curate=curate,
            skip_moderation=skip_moderation,
            debug_content_id=debug_content_id,
        )

        streak, _, __ = QuestComment.posting_would_reward_streak(author)
        if streak:
            economy.credit_streak(author, streak)

        if was_first_quest:
            economy.credit_first_quest(author)
        elif was_quest_of_the_day:
            economy.credit_quest_of_the_day_completion(author)
        elif was_archived_quest:
            economy.credit_archived_quest_completion(author)

        @bgwork.defer
        def followee_posted():
            Actions.followee_posted(author, comment)

            #TODO this should happen because of the above Actions.followee_posted
            for follower_id in author.redis.new_followers.zrange(0, -1):
                RealtimeChannel('user:{}:rt_tab_badges'.format(follower_id), 1).publish({'tab_badge_update': 'home'})

        return comment

    @classmethod
    def by_author(cls, author):
        return cls.objects.filter(author=author).order_by('-id')

    @property
    def playback_filename(self):
        return '{}-{}.json.gz'.format(self.reply_content_id, self.id)

    def visibility_changed(self, force_cache=True):
        if force_cache:
            self.quest.details.force()
            self.details.force()
        else:
            self.quest.details.invalidate()
            self.details.invalidate()

        self.update_score()

        if self.visibility not in [Visibility.PUBLIC, Visibility.CURATED]:
            self.author.redis.feed_source.remove(self.id)

        visibility_changed_signal.send(Comment, instance=self)

    def get_stars(self):
        """
        Returns a list of `{username, timestamp, id}` dicts.
        """
        stickers = CommentSticker.objects.filter(comment=self, type_id=settings.STAR_STICKER_TYPE_ID)
        stickers = stickers.values('user_id', 'timestamp', 'id')
        return [
            {
                'user': User.details_by_id(sticker['user_id'])(),
                'timestamp': sticker['timestamp'],
                'id': sticker['id'],
            }
            for sticker in stickers
        ]

    def get_reactions(self):
        """
        Includes just stars and playbacks, for now, interleaved by timestamp.
        """
        stars = self.get_stars()
        for star in stars:
            star['reaction_type'] = 'star'

        playbacks = [{
            'id': playback.id,
            'user': UserDetails.from_id(playback.viewer_id),
            'timestamp': playback.timestamp,
            'reaction_type': 'playback',
        } for playback in self.playbacks.all()]

        reactions = itertools.chain(stars, playbacks)
        return sorted(reactions, key=lambda reaction: reaction['timestamp'], reverse=True)

    def _details(self):
        content_details = self.reply_content.details().to_backend() if self.reply_content else {}

        return {
            'author_id': self.author_id,
            'content': content_details,
            'id': self.id,
            'quest_id': self.parent_comment_id,
            'quest_title': self.parent_comment.title,
            'reply_count': self.get_replies().count(),
            'timestamp': self.timestamp,
            'reactions': self.get_reactions(),
            'star_count': len(self.get_stars()),
            'playback_count': self.playbacks.count(),
            'posted_on_quest_of_the_day': self.posted_on_quest_of_the_day,

            # Shims for canvas internals.
            'sticker_counts': self.get_sticker_counts(),
            'repost_count': 0,
            'visibility': self.visibility,
        }

    @classmethod
    def details_by_id(cls, comment_id, promoter=None):
        from drawquest.apps.quest_comments.details_models import QuestCommentDetails

        if promoter is None:
            promoter = QuestCommentDetails

        def inner_call():
            return cls.all_objects.get(id=comment_id)._details()

        return CachedCall(
            'quest_comment:{}:details_v18'.format(comment_id),
            inner_call,
            14*24*60*60,
            promoter=promoter,
        )

    @property
    def quest(self):
        return self.parent_comment

    @property
    def details(self):
        return self.details_by_id(self.id)

    @property
    def flagged_details(self):
        #TODO: create a more elegant role syystem for comment detail types
        from canvas.details_models import FlaggedCommentDetails
        return QuestComment.details_by_id(self.id, promoter=FlaggedCommentDetails)

    def star(self, user):
        from drawquest.apps.stars.models import star
        return star(user, self)

    def unstar(self, user):
        from drawquest.apps.stars.models import unstar
        return unstar(user, self)

    def get_share_page_url(self, absolute=False):
        url = '/p/{}'.format(util.base36encode(self.id))
        if absolute:
            url = 'http://' + settings.DOMAIN + url
        return url

def add_viewer_has_starred_field(comment_details, viewer=None):
    if viewer is None or not viewer.is_authenticated():
        return comment_details

    for comment in comment_details:
        comment.viewer_has_starred = comment.has_viewer_starred(viewer)

def user_comments(user, viewer, offset='top', include_ugq=True, include_reactions=True):
    comments = QuestComment.by_author(user)

    if not include_ugq:
        comments = comments.filter(parent_comment__ugq=False)

    if viewer.id != user.id:
        comments = comments.exclude(visibility=Visibility.CURATED)

        if viewer.is_authenticated():
            comments = comments.exclude(flags__user=viewer)

    pagination = Paginator(comments, knobs.COMMENTS_PER_PAGE, offset=offset)

    comments = pagination.items

    promoter = None if include_reactions else QuestCommentGalleryDetails
    comments = CachedCall.queryset_details(comments, promoter=promoter)

    add_viewer_has_starred_field(comments, viewer=viewer)

    return comments, pagination


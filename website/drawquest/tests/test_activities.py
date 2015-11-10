from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment)
from canvas.exceptions import ServiceError, ValidationError
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.stars import models as star_models
from services import Services, with_override_service, FakeTimeProvider
from apps.activity.redis_models import ActivityStream
from drawquest.activities import StarredActivity, FolloweePostedActivity, FolloweeCreatedUgqActivity
from drawquest.apps.quests.models import Quest


class TestActivities(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
        self.actor = create_user()

    def _get_items(self, params={}):
        return self.api_post('/api/activity/activities', params, user=self.user)['activities']

    def test_actor_avatar(self):
        avatar = create_content()
        self.api_post('/api/user/change_avatar', {'content_id': avatar.id}, user=self.actor)

        comment = create_quest_comment(author=self.user)
        star_models.star(self.actor, comment)

        sticker = comment.stickers.all()[0]
        stream = ActivityStream(self.user.id, activity_types=[StarredActivity])
        activity = StarredActivity.from_sticker(self.actor, sticker)
        stream.push(activity)

        activity, _ = list(self.user.redis.activity_stream)
        self.assertTrue('avatar_url' in activity.to_client()['actor'])

    def _followee_post(self):
        """ Returns the posted comment. """
        self.user.follow(self.actor)
        comment = create_quest_comment(author=self.actor)

        stream = ActivityStream(self.user.id, activity_types=[FolloweePostedActivity])
        activity = FolloweePostedActivity.from_comment(self.actor, comment)
        stream.push(activity)

        return comment

    def test_followee_posted(self):
        comment = self._followee_post()
        activity, _ = list(self.user.redis.activity_stream)
        self.assertEqual(activity.to_client()['comment_id'], comment.id)

    def test_followee_created_ugq(self):
        self.user.follow(self.actor)
        resp = self.api_post('/api/ugq/create_quest', {
            'title': 'Test',
            'content_id': None,
        }, user=self.actor)
        quest = Quest.objects.get(id=resp['quest']['id'])

        stream = ActivityStream(self.user.id, activity_types=[FolloweeCreatedUgqActivity])
        activity = FolloweeCreatedUgqActivity.from_quest(self.actor, quest)
        stream.push(activity)

        activities = list(self.user.redis.activity_stream)
        print activities
        activity = activities[0]
        self.assertEqual(activity.to_client()['quest_id'], quest.id)

    @with_override_service('time', FakeTimeProvider)
    def test_later_than(self):
        comments = []
        for _ in range(3):
            comments.append(self._followee_post())
            Services.time.step()

        for a in self._get_items(params={'later_than': comments[0].timestamp}):
            print a['ts'],
            print a['type']

        print 'target:',comments[0].timestamp

        items = self._get_items(params={'later_than': comments[0].timestamp})
        self.assertEqual(len([item for item in items if item['type'] == 'followee_posted']), 2)

    @with_override_service('time', FakeTimeProvider)
    def test_earlier_than(self):
        comments = []
        for _ in range(3):
            comments.append(self._followee_post())
            Services.time.step()

        for a in self._get_items(params={'earlier_than': comments[2].timestamp}):
            print a['ts'],
            print a['type']

        print 'target:',comments[2].timestamp

        items = self._get_items(params={'earlier_than': comments[2].timestamp})
        self.assertEqual(len([item for item in items if item['type'] == 'followee_posted']), 2)

    def test_cache_invalidation(self):
        original_len = len(self._get_items())

        self.user.follow(self.actor)
        comment = create_quest_comment(author=self.actor)

        stream = ActivityStream(self.user.id, activity_types=[FolloweePostedActivity])
        activity = FolloweePostedActivity.from_comment(self.actor, comment)
        stream.push(activity)

        self.assertEqual(len(self._get_items()), original_len + 1)
 

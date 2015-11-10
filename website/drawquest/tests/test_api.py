from datetime import timedelta as td
import hashlib

from django.conf import settings
from django.conf.urls import url, patterns, include

from drawquest.api_cache import cached_api
from drawquest.apps.palettes.models import Color, ColorPack
from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment,
                                           fake_api_request)
from drawquest.api_decorators import api_decorator
from drawquest.apps.brushes.models import Brush
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.drawquest_auth.models import User
from canvas.exceptions import ServiceError, ValidationError
from drawquest import knobs
from canvas import util
from apps.share_tracking.models import ShareTrackingUrl
from canvas.models import Visibility, FacebookUser
from services import Services, override_service


class TestProfile(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()
    
    def test_bio(self):
        bio = 'my new bio'
        self.api_post('/api/user/change_profile', {'bio': bio}, user=self.user)
        self.assertEqual(self.api_post('/api/user/profile', {'username': self.user.username})['bio'], bio)

    def test_realtime_sync(self):
        resp = self.api_post('/api/realtime/sync', user=self.user)
        self.assertAPISuccess(resp)
        self.assertTrue(self.user.redis.activity_stream_channel.channel in resp['channels'])

    def test_create_share_url_for_channel_via_api(self):
        cmt = create_quest_comment()
        result = self.api_post('/api/share/create_for_channel',
                               {'comment_id': cmt.id, 'channel': 'testing'}, user=self.user)
        self.assertAPISuccess(result)
        url = result['share_url']
        rmatch = '/s/{}'.format(util.base36encode(ShareTrackingUrl.objects.order_by('-id')[0].id))
        self.assertEqual(url[url.rfind(rmatch):], rmatch)

    def test_create_share_url_for_channel_has_message_for_twitter(self):
        cmt = create_quest_comment()
        result = self.api_post('/api/share/create_for_channel',
                               {'comment_id': cmt.id, 'channel': 'twitter'}, user=self.user)
        self.assertTrue('message' in result)

    def test_heavy_state_sync(self):
        state = self.api_post('/api/heavy_state_sync', user=self.user)
        self.assertAPISuccess(state)
        self.assertEqual(state['user_profile']['user']['username'], self.user.username)

    def test_heavy_state_sync_with_fb_user(self):
        FacebookUser.objects.create(user=self.user, fb_uid='123')
        state = self.api_post('/api/heavy_state_sync', user=self.user)
        self.assertAPISuccess(state)
        self.assertEqual(state['user_profile']['facebook_url'], 'https://facebook.com/123')

    def test_heavy_state_sync_with_tab_badges(self):
        state = self.api_post('/api/heavy_state_sync', {'tab_last_seen_timestamps': {'activity': 500}}, user=self.user)
        self.assertAPISuccess(state)
        self.assertTrue('tab_badges' in state)

    def test_twitter_privacy_default(self):
        state = self.api_post('/api/heavy_state_sync', user=create_user())
        self.assertEqual(state['twitter_privacy'], None)


class TestEmailHashes(CanvasTestCase):
    def test_successful(self):
        email = 'email@dmauro.com'
        user = create_user()
        self.api_post('/api/user/change_profile', {'new_email': email}, user=user)
        hashed = hashlib.sha1(email).hexdigest()
        resp = self.api_post('/api/existing_users_by_email', {'email_hashes': [hashed]})
        self.assertAPISuccess(resp)
        self.assertEqual(resp['users'][0]['username'], user.username)


class TestFlags(CanvasTestCase):
    def test_auto_moderation_from_flags(self):
        cmt = create_quest_comment()

        for i in range(1, knobs.AUTO_DISABLE_FLAGGED_COMMENTS_THRESHOLD[None] + 1):
            resp = self.api_post('/api/comment/flag', {'comment_id': cmt.id})

            cmt = QuestComment.all_objects.get(pk=cmt.pk)
            getattr(self, 'assert' + str(i == knobs.AUTO_DISABLE_FLAGGED_COMMENTS_THRESHOLD[None]))(
                cmt.visibility == Visibility.DISABLED)

        self.assertTrue(cmt.id in [qc.id for qc in QuestComment.unjudged_flagged()])

    def test_self_flag(self):
        cmt = create_quest_comment()
        resp = self.api_post('/api/comment/flag', {'comment_id': cmt.id}, user=cmt.author)


class TestCache(CanvasTestCase):
    def after_setUp(self):
        urls = patterns('')
        self.api = api_decorator(urls)

    def _api(self, api_func, data={}):
        return util.loads(api_func(fake_api_request('', data=data)).content)

    def test_cache_hit(self):
        i = [0]

        @self.api('test_cache')
        @cached_api(td(days=2), key='test_cache')
        def test_cache(request):
            i[0] += 1
            return {'i': i[0]}

        for _ in range(2):
            print self._api(test_cache)
            self.assertEqual(self._api(test_cache)['i'], 1)

    def test_uncached(self):
        i = [0]

        @self.api('test_uncached')
        def test_cache(request):
            i[0] += 1
            return {'i': i[0]}

        for j in range(1, 2):
            self.assertEqual(self._api(test_cache)['i'], j)


class TestConfig(CanvasTestCase):
    def test_fs(self):
        self.assertTrue('drawquest' in settings.IMAGE_FS[1])


class TestKV(CanvasTestCase):
    def test_set(self):
        user = create_user()
        items = {'saw_update_modal_for_version': 'bar'}
        self.assertAPISuccess(self.api_post('/api/kv/set', {'items': items}, user=user))

        state = self.api_post('/api/heavy_state_sync', user=user)
        self.assertAPISuccess(state)
        self.assertEqual(state['user_kv']['saw_update_modal_for_version'], 'bar')


class TestShop(CanvasTestCase):
    def test_for_nothing_bought(self):
        color = Color.objects.create(
            red=255,
            green=255,
            blue=255,
            owned_by_default=True,
            label='White',
            ordinal=1,
        )
        resp = self.api_post('/api/shop/all_items')
        self.assertAPISuccess(resp)
        self.assertEqual(resp['shop_colors'][0]['label'], 'White')

    def test_brushes(self):
        brush = Brush.objects.create(
            ordinal=0,
            canonical_name='paintbrush',
            label='Paintbrush',
            cost=50,
            is_for_sale=True,
            is_new=True,
            red=0,
            green=0,
            blue=0,
        )
        resp = self.api_post('/api/shop/all_items')
        self.assertAPISuccess(resp)
        self.assertEqual(resp['shop_brushes'][0]['label'], 'Paintbrush')


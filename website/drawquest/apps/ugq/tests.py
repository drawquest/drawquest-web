# -*- coding: utf-8 -*-

from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff, create_quest, create_quest_comment)
from canvas.models import Visibility
from drawquest.apps.quests.models import Quest
from drawquest.apps.drawquest_auth.models import AnonymousUser
from services import Services, override_service


class TestQuestCreation(CanvasTestCase):
    def after_setUp(self):
        self.author = create_user()

    def test_create_without_content(self):
        resp = self.api_post('/api/ugq/create_quest', {
            'title': 'Test',
            'content_id': None,
        }, user=self.author)
        self.assertAPISuccess(resp)

    def test_share_page_without_content(self):
        resp = self.api_post('/api/ugq/create_quest', {
            'title': 'Test',
            'content_id': None,
        }, user=self.author)
        self.assertStatus(200, Quest.objects.get(id=resp['quest']['id']).get_share_page_url(), user=AnonymousUser())

    def test_flag_word(self):
        title = 'foo bar shit baz'
        resp = self.api_post('/api/ugq/create_quest', {
            'title': title,
            'content_id': None,
        }, user=self.author)
        self.assertAPISuccess(resp)
        quest = Quest.all_objects.get(title=title)
        self.assertEqual(quest.visibility, Visibility.CURATED)

    #def test_create_with_unicode_title(self):
    #    title = u'テスト'
    #    resp = self.api_post('/api/ugq/create_quest', {
    #        'title': title,
    #        'content_id': None,
    #    }, user=self.author)
    #    self.assertAPISuccess(resp)

    #    self.assertEqual(Quest.objects.filter(ugq=True)[0].title, title)

    #    resp = self.api_post('/api/ugq/quests_created_by_user', {
    #        'username': self.author.username,
    #    })
    #    self.assertAPISuccess(resp)

    #    self.assertEqual(resp['quests'][0]['title'], title)


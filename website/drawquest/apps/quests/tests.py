from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment)
from drawquest import knobs
from services import Services, override_service


COMMENTS_PER_PAGE = 2


class TestQuestApi(CanvasTestCase):
    def after_setUp(self):
        self.old_quest = create_current_quest()
        self.quest = create_current_quest()
        self.user = create_user()
        knobs.ONBOARDING_QUEST_ID = self.quest.id

        self.comments_per_page = knobs.COMMENTS_PER_PAGE
        knobs.COMMENTS_PER_PAGE = COMMENTS_PER_PAGE

    def before_tearDown(self):
        knobs.COMMENTS_PER_PAGE = self.comments_per_page

    def test_quest_archive(self):
        for api_version in ['1.0.1', None]:
            archive = self.api_post('/api/quests/archive', api_version=api_version)['quests']
            self.assertEqual(len(archive), 1)
            self.assertEqual(archive[0]['id'], self.old_quest.id)

    def test_quest_inbox_for_qotd(self):
        resp = self.api_post('/api/quests/inbox')
        self.assertAPISuccess(resp)

        current = resp['current_quest']
        self.assertEqual(current['id'], self.quest.id)

    def test_empty_quest_inbox(self):
        create_quest_comment(quest=self.quest, author=self.user)

        resp = self.api_post('/api/quests/inbox', user=self.user)
        self.assertAPISuccess(resp)

        self.assertEqual(0, len(resp['quests']))
        self.assertFalse('current_quest' in resp)

    def test_quest_inbox_with_invite(self):
        inviter = create_user()
        self.api_post('/api/quest_invites/invite_user_to_quest', {
            'username': self.user.username,
            'quest_id': self.old_quest.id,
        }, user=inviter)

        resp = self.api_post('/api/quests/inbox', user=self.user)
        self.assertAPISuccess(resp)
        
        quests = resp['quests']
        self.assertEqual(quests[0]['id'], self.old_quest.id)

    def test_quest_inbox_with_followee_ugq(self):
        user = create_user()
        followee = create_user()
        user.follow(followee)

        ugq_resp = self.api_post('/api/ugq/create_quest', {
            'title': 'Test',
            'content_id': None,
        }, user=followee)

        resp = self.api_post('/api/quests/inbox', user=user)
        self.assertAPISuccess(resp)

        quests = resp['quests']
        self.assertEqual(quests[0]['id'], ugq_resp['quest']['id'])
        self.assertEqual(len(quests), 1)

    def test_empty_quest_inbox(self):
        create_quest_comment(quest=self.quest, author=self.user)

        resp = self.api_post('/api/quests/history', user=self.user)
        self.assertAPISuccess(resp)

        self.assertEqual(1, len(resp['quests']))
        self.assertEqual(resp['quests'][0]['id'], self.quest.id)

    def test_quest_dismissal(self):
        user = create_user()
        inviter = create_user()
        self.api_post('/api/quest_invites/invite_user_to_quest', {
            'username': user.username,
            'quest_id': self.old_quest.id,
        }, user=inviter)

        resp = self.api_post('/api/quests/inbox', user=user)
        self.assertAPISuccess(resp)

        self.assertEqual(resp['current_quest']['id'], self.quest.id)
        self.assertEqual(resp['quests'][0]['id'], self.old_quest.id)

        resp = self.api_post('/api/quests/dismiss_quest', {'quest_id': self.old_quest.id}, user=user)
        self.assertAPISuccess(resp)

        resp = self.api_post('/api/quests/inbox', user=user)
        self.assertTrue('current_quest' in resp)
        self.assertEqual(len(resp['quests']), 0)

    def test_quest_comments(self):
        cmt = create_quest_comment(self.quest)
        cmts = self.api_post('/api/quests/comments', {'quest_id': self.quest.id})['comments']
        self.assertEqual(cmts[0]['id'], cmt.id)

    def test_quest_comments_with_forced_id(self):
        cmt = create_quest_comment(self.quest)
        for _ in range(4):
            create_quest_comment(self.quest)

        def get_cmts():
            return self.api_post('/api/quests/comments', {
                'quest_id': self.quest.id,
                'force_comment_id': cmt.id,
            })['comments']

        cmts = get_cmts()
        self.assertTrue(str(cmt.id) in [str(c['id']) for c in cmts])
        self.assertEqual(len(cmts), COMMENTS_PER_PAGE + 1)

        cmt = create_quest_comment(self.quest)
        cmts = get_cmts()
        self.assertTrue(str(cmt.id) in [str(c['id']) for c in cmts])
        self.assertEqual(len(cmts), COMMENTS_PER_PAGE)

    def test_current_quest(self):
        quest = self.api_post('/api/quests/current')['quest']
        self.assertEqual(quest['id'], self.quest.id)

    def test_onboarding_quest(self):
        quest = self.api_post('/api/quests/onboarding')['quest']
        self.assertEqual(int(quest['id']), int(self.quest.id))


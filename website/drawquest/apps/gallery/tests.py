from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment)
from drawquest import knobs
from drawquest.apps.whitelisting.models import deny, curate
from services import Services, override_service


COMMENTS_PER_PAGE = 2


class TestGalleryApi(CanvasTestCase):
    def after_setUp(self):
        self.quest = create_current_quest()
        self.user = create_user()

        self.comments_per_page = knobs.COMMENTS_PER_PAGE
        knobs.COMMENTS_PER_PAGE = COMMENTS_PER_PAGE

    def before_tearDown(self):
        knobs.COMMENTS_PER_PAGE = self.comments_per_page

    def _gallery(self, quest, page='top'):
        return self.api_post('/api/quests/gallery', {'quest_id': self.quest.id})['comments']

    def _star(self, comment_id, user=None):
        resp = self.api_post('/api/stars/star', {'comment_id': comment_id}, user=user)
        self.assertAPISuccess(resp)
        return resp

    def test_quest_gallery(self):
        cmt = create_quest_comment(self.quest)
        cmts = self._gallery(self.quest)
        self.assertEqual(cmts[0]['id'], cmt.id)

    def test_cache_invalidation_from_star(self):
        cmt = create_quest_comment(self.quest)
        self._star(cmt.id)
        gallery = self.api_post('/api/quests/gallery_for_comment',
                                {'comment_id': cmt.id})['comments']
        self.assertEqual(1, gallery[0]['star_count'])

    def test_starred_comments_gallery(self):
        cmt = create_quest_comment(self.quest)
        user = create_user()
        self._star(cmt.id, user=user)
        gallery = self.api_post('/api/quest_comments/starred_comments_gallery',
                                {'username': user.username})['comments']
        self.assertEqual(cmt.id, gallery[0]['id'])

    def test_top_gallery(self):
        cmt = create_quest_comment(self.quest)
        self.api_post('/api/stars/star', {'comment_id': cmt.id})
        gallery = self.api_post('/api/quests/top_gallery',
                                {'quest_id': cmt.parent_comment_id})['comments']
        self.assertEqual(1, len(gallery))

    def test_quest_gallery_for_comment(self):
        cmt = create_quest_comment(self.quest)
        for _ in range(4):
            create_quest_comment(self.quest)

        def get_cmts():
            return self.api_post('/api/quests/gallery_for_comment', {
                'comment_id': cmt.id,
            })['comments']

        cmts = get_cmts()
        print [c['id'] for c in cmts]
        self.assertTrue(str(cmt.id) in [str(c['id']) for c in cmts])
        self.assertEqual(len(cmts), COMMENTS_PER_PAGE)

        cmt = create_quest_comment(self.quest)
        cmts = get_cmts()
        self.assertTrue(str(cmt.id) in [str(c['id']) for c in cmts])
        self.assertEqual(len(cmts), COMMENTS_PER_PAGE)
        
        curate(cmt)
        self.assertTrue(str(cmt.id) in [str(c['id']) for c in get_cmts()])

    def test_visibility_changes(self):
        cmt = create_quest_comment(self.quest)
        self._gallery(self.quest)

        deny(cmt)
        cmts = self._gallery(self.quest)
        self.assertFalse(cmt.id in [c['id'] for c in cmts])


from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff, create_quest, create_quest_comment)
from services import Services, override_service


class TestSimpleThing(CanvasTestCase):
    def after_setUp(self):
        self.user = create_user()

    def test_profile(self):
        self.assertStatus(200, '/' + self.user.username)

        for _ in range(10):
            cmt = create_quest_comment(author=self.user)
            self.api_post('/api/stars/star', {'comment_id': cmt.id})
        self.assertStatus(200, '/' + self.user.username)


from canvas import bgwork
from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff,
                                           create_quest, create_current_quest, create_quest_comment)
from services import Services, override_service


class TestFeed(CanvasTestCase):
    def test_loads(self):
        self.assertAPISuccess(self.api_post('/api/feed/followee_comments', user=create_user()))

    def test_loads_with_feed_item(self):
        user = create_staff()
        other = create_user()
        user.follow(other)

        cmt = self.post_quest_comment(author=other)['comment']

        resp = self.api_post('/api/feed/followee_comments', user=user)
        self.assertAPISuccess(resp)
        self.assertEqual(resp['comments'][0]['id'], cmt['id'])


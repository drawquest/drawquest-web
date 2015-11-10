from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group, create_comment,
                                        create_staff)
from services import Services, override_service


class TestFollowing(CanvasTestCase):
    def test_followers(self):
        user = create_user()
        follower = create_user()
        follower.follow(user)
        resp = self.api_post('/api/following/followers', {'username': user.username})
        self.assertAPISuccess(resp)
        self.assertEqual(resp['followers'][0]['username'], follower.username)


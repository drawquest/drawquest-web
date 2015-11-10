import os.path
import urlparse

from canvas.models import (Category, Comment, CommentPin, FollowCategory, CommentSticker, AnonymousUser, Visibility,
                           APIApp, APIAuthToken, Content, UserInfo)
from canvas.tests.tests_helpers import (CanvasTestCase, NotOkay, FakeRequest, create_content, create_user,
                                        create_group, redis, create_staff, create_comment)
from canvas import last_sticker, economy, stickers, bgwork, knobs
from canvas.api_decorators import api_decorator
from canvas.notifications.actions import Actions
from canvas.tests import tests_helpers
from canvas.util import get_or_create
from canvas.view_guards import require_POST
from services import Services, override_service, FakeTimeProvider, FakeMetrics
from django.conf import settings

STORE_ITEM = '103'


class TestApiDecorator(CanvasTestCase):
    def test_wrong_decorator_order(self):
        def wrong_order():
            api = api_decorator([])
            @require_POST
            @api('whatever', skip_javascript=True)
            def foo(request):
                pass
        self.assertRaises(TypeError, wrong_order)

    def test_correct_decorator_order(self):
        api = api_decorator([])
        @api('whatever', skip_javascript=True)
        @require_POST
        def foo(request):
            pass


class TestCommentDelete(CanvasTestCase):
    def test_deleting_doesnt_flag(self):
        cmt = self.post_comment(reply_content=create_content().id)
        self.assertNotEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.UNPUBLISHED)

        result = self.api_post('/api/comment/delete', {'comment_id': cmt.id}, user=cmt.author)
        self.assertEqual(result, {'success': True})
        self.assertEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.UNPUBLISHED)
        self.assertEqual(cmt.flags.count(), 0)

    def test_deleting_others_post_fails(self):
        cmt = self.post_comment(reply_content=create_content().id)
        result = self.api_post('/api/comment/delete', {'comment_id': cmt.id})
        self.assertEqual(result, {'success': False, 'reason': 'Not comment author'})
        self.assertEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.PUBLIC)

    def test_replying_doesnt_resurrect_post(self):
        cmt = self.post_comment(reply_content=create_content().id)
        result = self.api_post('/api/comment/delete', {'comment_id': cmt.id}, user=cmt.author)
        self.assertEqual(result, {'success': True})
        self.assertEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.UNPUBLISHED)

        reply = self.post_comment(parent_comment=cmt.id, reply_content=create_content().id)
        self.assertEqual(Comment.all_objects.get(id=cmt.id).visibility, Visibility.UNPUBLISHED)


class TestCommentFlag(CanvasTestCase):
    def setUp(self):
        super(TestCommentFlag, self).setUp()
        self._old_limits = knobs.FLAG_RATE_LIMITS
        knobs.FLAG_RATE_LIMITS = {
            'm': (2, 2*60,), # Lower frequency so that the runs faster.
            'h': (50, 60*60,),
        }

    def _test_rate_limit(self, user, allowed):
        with override_service('time', FakeTimeProvider, kwargs={'t': 1333333333.}):
            client = self.get_client(user=user)
            flag_count = min(freq for freq,timespan in knobs.FLAG_RATE_LIMITS.itervalues()) + 1
            cmts = [self.post_comment(reply_content=create_content().id) for _ in xrange(flag_count)]
            msg = None
            for cmt in cmts:
                resp = self.api_post('/api/comment/flag', {'comment_id': cmt.id}, client=client)
                if not resp['success']:
                    msg = resp['reason']
                    break
            getattr(self, {True: 'assertEqual', False: 'assertNotEqual'}[allowed])(msg, None)
            if not allowed:
                self.assertTrue('limit' in msg)

    def test_rate_limit_exceeded(self):
        self._test_rate_limit(create_user(), False)

    def test_staff_exemption(self):
        self._test_rate_limit(create_staff(), True)

    def tearDown(self):
        knobs.FLAG_RATE_LIMITS = self._old_limits
        super(TestCommentFlag, self).tearDown()


class TestCommentPost(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.group = create_group()
        self.original = create_content()
        self.op = self.post_comment(reply_content=self.original.id, category=self.group.name)
        self.remix = create_content()
        self.remix.remix_of = self.original
        self.remix.save()

    def test_comment_reply(self):
        comment = self.post_comment(reply_content=create_content().id, parent_comment=self.op.id)
        self.assertTrue(self.op.id > 0)
        self.assertEqual(comment.parent_comment.id, self.op.id)

    def test_remix_works_when_allowed(self):
        result = self.post_comment(parent_comment=self.op.id,
                                   reply_content=self.remix.id,
                                   category=self.group.name,
                                   fetch_comment=False)
        self.assertEqual(result['success'], True)


class TestCommentValidation(CanvasTestCase):
    def test_valid_post(self):
        kwargs = {
            'reply_content': create_content().id,
            'parent_comment': create_content().id,
        }
        response = self.api_post('/api/comment/validate_post', kwargs)
        self.assertAPISuccess(response)

    def test_invalid_post(self):
        kwargs = {
            'category': "this group doesn't exist",
        }
        response = self.api_post('/api/comment/validate_post', kwargs)
        self.assertAPIFailure(response)


class TestPostComment(CanvasTestCase):
    def mock_call_count(self, *args, **kwargs):
        self.call_count += 1

    def after_setUp(self):
        self.old_func = Actions.replied
        Actions.replied = self.mock_call_count

    def before_tearDown(self):
        Actions.replied = self.old_func

    def test_posting_comment_creates_notification(self):
        self.call_count = 0

        self.post_comment(reply_content=create_content().id)
        assert self.call_count == 1


class TestFollow(CanvasTestCase):
    def test_follow(self):
        user = create_user()
        group = create_group()
        result = self.api_post('/api/group/follow', {'category_id': group.id}, user=user)

        self.assertEqual(result['success'], True)
        fc = FollowCategory.objects.get_or_none(category=group, user=user)
        self.assertTrue(bool(fc))

    def test_unfollow(self):
        user = create_user()
        group = create_group()
        result = self.api_post('/api/group/follow', {'category_id': group.id}, user=user)
        result = self.api_post('/api/group/unfollow', {'category_id': group.id}, user=user)

        self.assertEqual(result['success'], True)
        fc = FollowCategory.objects.get_or_none(category=group, user=user)
        self.assertFalse(bool(fc))


class TestUserAPI(CanvasTestCase):
    def test_logged_out_user_more(self):
        user = create_user()
        result = self.api_post('/api/user/more', {'offset': 30, 'nav_data': {'user': user.username, 'userpage_type': "top", 'include_anonymous': ""}}, user=user)
        self.assertEqual(result.strip(), '')

    def test_parameterless_user_more(self):
        try:
            resp = self.api_post('/api/user/more')
        except NotOkay, e:
            self.assertEqual(e.status, 404)
        else:
            raise Exception("Didn't return 404")

    def test_user_doesnt_exist(self):
        resp = self.api_post('/api/user/exists', {'username': 'foo_no_exist'})
        self.assertAPISuccess(resp)

    def test_user_exists(self):
        user = create_user()
        resp = self.api_post('/api/user/exists', {'username': user.username})
        self.assertAPIFailure(resp)


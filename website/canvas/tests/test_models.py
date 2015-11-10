# -*- coding: utf-8 -*-
import datetime, time

from boto.exception import BotoServerError
from django.core.exceptions import PermissionDenied
from django.http import Http404

from apps.canvas_auth.models import User, AnonymousUser
from canvas.browse import (get_browse_tiles, get_user_stickered, TileDetails, LastReplyTileDetails,
                           get_front_comments, Navigation, get_user_data)
from canvas.management.commands import send_24h_email
from canvas.models import (Comment, Visibility, CommentSticker,
                           send_email, WelcomeEmailRecipient, flagged_comments, Content)
from canvas.details_models import CommentDetails
from canvas.tests.tests_helpers import (create_comment, create_content, create_user, CanvasTestCase,
                                        FakeRequest, create_staff, create_rich_user)
from canvas import api, stickers, mocks, util
from canvas.notifications.email_channel import EmailChannel
from configuration import Config
from services import Services, override_service, FakeTimeProvider, FakeMetrics, FakeExperimentPlacer


class TestCommentStickers(CanvasTestCase):
    def test_sticker_from_user(self):
        user = create_user()
        comment = create_comment()
        self.assertFalse(CommentSticker.get_sticker_from_user(comment.id, user))

        self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': comment.id}, user=user)
        self.assertTrue(CommentSticker.get_sticker_from_user(comment.id, user))


class TestUserData(CanvasTestCase):
    def test_user_stickered_deleted_comment(self):
        cmt = self.post_comment(reply_content=create_content().id)

        # Now another user sticks it.
        user = create_user()
        result = self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': cmt.id}, user=user)

        # Then the author deletes it.
        self.api_post('/api/comment/delete', {'comment_id': cmt.id}, user=cmt.author)

        stickered = get_user_stickered(user)
        self.assertEqual(len(stickered), 0)

    def test_user_data_with_invalid_type_404s(self):
        user = create_user()
        nav_data = {'userpage_type': 'stickered', 'user': create_user().username}
        nav = Navigation.load_json_or_404(nav_data)
        nav.userpage_type = 'INVALID_TYPE'
        self.assertRaises(Http404, lambda: get_user_data(user, nav))


class TestCommentDetails(CanvasTestCase):
    def after_setUp(self):
        # Create a bunch of comments
        for i in range(1, 10):
            create_comment(author=create_user())
        self.comments = Comment.all_objects.all()

    def test_from_queryset_with_pins(self):
        self.assertTrue(self.comments)

        tiles = TileDetails.from_queryset_with_pins(self.comments)
        self.assertTrue(tiles)
        for tile in tiles:
            self.assertNotEqual(tile.pins, None)
            self.assertIsInstance(tile.comment, CommentDetails)

    def test_from_queryset_with_viewer_stickers(self):
        user = create_user()
        def tiles():
            return TileDetails.from_queryset_with_viewer_stickers(user, self.comments)

        for tile in tiles():
            self.assertEqual(tile.viewer_sticker, None)
            self.api_post('/api/sticker/comment', {'type_id': '1', 'comment_id': tile.comment.id},
                          user=user)

        for tile in tiles():
            self.assertEqual(tile.viewer_sticker.type_id, 1)

    def test_properties_dont_get_serialized(self):
        # CommentDetails should only serialize its dict contents, not any of its member properties.
        cmt = create_comment().details()
        cmt.test_foo_property = 1

        d = util.loads(util.dumps(cmt))
        self.assertFalse('test_foo_property' in d)

    def test_empty_reply_content(self):
        cmt = create_comment().details()
        self.assertEqual(cmt.reply_content, {})


class TestCommentDetailsStickers(CanvasTestCase):
    def _make_stickers(self, sticks=['smiley', 'banana', 'frowny', 'frowny'], top='banana', per=2):
        self.top_id = stickers.get(top).type_id
        self.stickers = map(stickers.get, sticks)
        self.cmt = self.post_comment(reply_content=create_content().id)
        from canvas import economy
        for sticker in self.stickers:
            for _ in xrange(per):
                user = create_rich_user()
                if sticker.cost:
                    user.kv.stickers.add_limited_sticker(sticker)
                    economy.purchase_stickers(user, sticker.type_id, 1)
                    #user.redis.user_kv.hset('sticker:%s:count' % STORE_ITEM, 1)
                self.api_post('/api/sticker/comment', {
                    'type_id': sticker.type_id,
                    'comment_id': self.cmt.id,
                }, user=user)

    def test_sorted_sticker_counts(self):
        self._make_stickers()
        counts = self.cmt.details().sorted_sticker_counts()
        self.assertEqual(counts[0]['type_id'], self.top_id)
        self.assertEqual(counts[0]['count'], 2)

    def test_top_sticker(self):
        self._make_stickers()
        top_stick = self.cmt.details().top_sticker()
        self.assertFalse(top_stick is None)
        self.assertEqual(top_stick['type_id'], self.top_id)

    def test_smiley_vs_frowny(self):
        self._make_stickers()
        counts = self.cmt.details().sorted_sticker_counts()
        self.assertEqual(counts[2]['type_id'], stickers.get('smiley').type_id)
        self.assertEqual(counts[1]['type_id'], stickers.get('frowny').type_id)

    def test_num1(self):
        self._make_stickers(sticks=['cool', 'smiley'], top='cool', per=1)
        top_stick = self.cmt.details().top_sticker()
        self.assertEqual(top_stick['type_id'], self.top_id)


class TestComment(CanvasTestCase):
    def test_get_deep_replies(self):
        op = create_comment()
        def reply(to):
            return create_comment(parent_comment=op, replied_comment=to)
        r1 = reply(op)
        r2 = reply(op)
        r3 = reply(op)
        r4 = reply(r3)
        r5 = reply(r4)
        r6 = reply(r4)
        r7 = reply(op)
        self.assertEqual(len(r3.get_deep_replies()), 3)
        r8 = reply(r3)
        self.assertEqual(len(r3.get_deep_replies()), 4)

    def test_update_score(self):
        user = create_user()
        comment = create_comment(author=user)

        for sticker in stickers.primary_types:
            user = create_user()
            user.kv.stickers.currency.increment(100)
            # Sticker the comment a bunch.
            request = FakeRequest(user)
            api._sticker_comment(request, comment, sticker.type_id)

        # Update score
        comment.update_score()

    def test_details_replies_no_replies(self):
        cmt = create_comment(timestamp=123)
        d = cmt.details()

        self.assertEqual(d.reply_count, 0)
        self.assertEqual(d.last_reply_id, None)
        # This should be the timestamp of the OP in this case.
        self.assertEqual(d.last_reply_time, 123)

    def test_details_replies_one_reply(self):
        with override_service('time', FakeTimeProvider):
            cmt = create_comment()
            Services.time.step()
            child = create_comment(parent_comment=cmt)
            d = cmt.details()

            self.assertEqual(d.reply_count, 1)
            self.assertEqual(d.last_reply_id, child.id)
            self.assertAlmostEqual(d.last_reply_time, child.timestamp, places=4)

    def test_details_replies_two_replies(self):
        cmt = create_comment()
        first = create_comment(parent_comment=cmt, timestamp=1)
        second = create_comment(parent_comment=cmt, timestamp=2)
        d = cmt.details()

        self.assertEqual(d.reply_count, 2)
        self.assertEqual(d.last_reply_id, second.id)
        self.assertEqual(d.last_reply_time, second.timestamp)

    def test_details_disabled_parent_url(self):
        cmt = self.post_comment(reply_content=create_content().id)
        reply = self.post_comment(parent_comment=cmt.id, reply_content=create_content().id)
        self.assertNotEqual(cmt.details().url, None)
        self.assertEqual(reply.details().parent_url, cmt.details().url)

        cmt.moderate_and_save(Visibility.UNPUBLISHED, cmt.author)
        self.assertEqual(reply.details.force().parent_url, None)

    def test_details_replies_two_replies_last_curated(self):
        # The last reply should include curated replies to prevent "stuck" active/pinned curated OPs auto-curating
        # their replies.
        cmt = create_comment()
        first = create_comment(parent_comment=cmt, timestamp=1)
        second = create_comment(parent_comment=cmt, timestamp=2)
        second.moderate_and_save(Visibility.CURATED, second.author)
        d = cmt.details()

        self.assertEqual(d.reply_count, 2)
        self.assertEqual(d.last_reply_id, second.id)
        self.assertEqual(d.last_reply_time, second.timestamp)


class TestContent(CanvasTestCase):
    def after_setUp(self):
        self.old_function = Content._get_details

    def before_tearDown(self):
        Content._get_details = self.old_function

    def test_details_does_not_trigger_recursion(self):
        that = self
        def test_wrapper(self, **kwargs):
            test_wrapper.calls_to_get_details += 1
            return that.old_function(self, **kwargs)

        test_wrapper.calls_to_get_details = 0

        Content._get_details = test_wrapper

        op = create_comment(reply_content=create_content())
        reply = op
        for i in range(4):
            last = reply
            reply = create_comment(parent_comment=op,
                                   reply_content=create_content(remix_of=last.reply_content))

        reply.details()
        self.assertEqual(test_wrapper.calls_to_get_details, 2)


class TestLastReplyTileDetails(CanvasTestCase):
    def test_in_reply_to(self):
        op = create_comment()
        reply = create_comment(parent_comment=op)
        tile = LastReplyTileDetails.from_comment_id(op.id)
        self.assertEqual(tile.comment.thread.op.id, op.id)


class TestCanvasUser(CanvasTestCase):
    def test_unsubscribe(self):
        user = create_user()

        # Sanity checks
        # Note that the default is the EmailChannel.
        assert user.kv.subscriptions
        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))

        # Now unsubscribe
        user.kv.subscriptions.unsubscribe('remixed')
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))


class TestUserKV(CanvasTestCase):
    def setUp(self):
        CanvasTestCase.setUp(self)
        self.sticker = stickers.Sticker(1234, "foobar", limited=True, maximum=10, cost=10)
        stickers.add_sticker(self.sticker)

    def tearDown(self):
        CanvasTestCase.tearDown(self)
        stickers.remove_sticker(self.sticker)

    def test_sticker_kv_purchase_markers(self):
        sticker = self.sticker
        user = create_user()

        assert user.kv.stickers.did_purchase(sticker) == False
        user.kv.stickers.mark_sticker_purchased(sticker)
        assert user.kv.stickers.did_purchase(sticker) == True


class TestEmail(CanvasTestCase):
    def test_ses_blacklist_silently_fails(self):
        def send_fail(messages):
            raise BotoServerError(400, "Bad Request",
            """<ErrorResponse xmlns="http://ses.amazonaws.com/doc/2010-12-01/">
                 <Error>
                   <Type>Sender</Type>
                   <Code>MessageRejected</Code>
                   <Message>Address blacklisted.</Message>
                 </Error>
                 <RequestId>a693e02d-00f2-11e1-9a52-ed3836840b28</RequestId>
               </ErrorResponse>""")

        with mocks.override_send_messages(send_fail):
            send_email('to@example.com', 'from@example.com', 'subjek', 'test', {})

    def test_repeating_exception_bubbles_out(self):
        def send_fail(messages):
            raise Exception

        with self.assertRaises(Exception):
            with mocks.override_send_messages(send_fail):
                send_email('a@b.com', 'b@c.com', 'subjek', 'test', {})


class TestWelcomeEmailRecipients(CanvasTestCase):
    def test_already_received(self):
        with override_service('time', FakeTimeProvider):
            # Create dummy first, so count of users and count of recipients is unequal.
            create_user()
            Services.time.step(60*60*48)

            user = create_user()
            self.assertFalse(user in send_24h_email.recipients())

            Services.time.step(60*60*48)
            WelcomeEmailRecipient.objects.create(recipient=user)
            recipients = send_24h_email.recipients()
            self.assertFalse(user in recipients)
            self.assertFalse(recipients)

    def test_not_yet_receieved(self):
        with override_service('time', FakeTimeProvider):
            user = create_user()
            Services.time.step(60*60*24)
            recipients = send_24h_email.recipients()
            self.assertTrue(user in recipients)

    def test_send_email_happens_once_per_recipient(self):
        with override_service('time', FakeTimeProvider):
            user = create_staff()
            Services.time.step(60*60*24)
            (recipient,) = send_24h_email.recipients()
            self.assertEqual(recipient, user)

            with override_service('metrics', FakeMetrics):
                def send():
                    for user in send_24h_email.recipients():
                        send_24h_email.send_welcome_email(user)
                self.assertEqual(0, len(Services.metrics.email_sent.records))
                send()
                self.assertEqual(1, len(Services.metrics.email_sent.records), "The digest email wasn't sent.")
                send()
                self.assertEqual(1, len(Services.metrics.email_sent.records), "The email was sent twice.")

    def test_really_old_users_dont_get_it(self):
        with override_service('time', FakeTimeProvider):
            user = create_user()
            Services.time.step(60*60*24)
            self.assertTrue(user in send_24h_email.recipients())
            Services.time.step(60*60*24*30) # a month later.
            self.assertFalse(user in send_24h_email.recipients())


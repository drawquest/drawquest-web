import copy
import logging
import random
import urllib

from django.contrib.sessions.backends.cache import SessionStore
from django.contrib.sessions.models import Session
from django.core.urlresolvers import reverse
from django.http import Http404
import facebook

from apps.canvas_auth.models import User, AnonymousUser
from apps.signup.views import signup, get_signup_context
from canvas import bgwork, stickers, views, util, knobs
from canvas.models import (Visibility, get_system_user, Config, Category, FacebookUser,
                           EmailUnsubscribe, APIApp, APIAuthToken, CommentSticker, Comment)
from canvas.notifications.email_channel import EmailChannel
from canvas.notifications.notification_models import UserNotificationsSubscription
from canvas.templatetags import canvas_tags
from canvas.tests.tests_helpers import (CanvasTestCase, create_content, create_group, create_user, create_staff,
                                        create_comment, create_gif_content, FakeRequest, pretty_print_etree)
from canvas.util import get_or_create, dumps
import configuration
from services import Services, override_service, FakeTimeProvider, FakeRandomProvider, FakeExperimentPlacer


class TestEmailViews(CanvasTestCase):
    def test_user_id_token_allows_unsubscribe(self):
        user = create_user()
        url = "/unsubscribe?" + urllib.urlencode({
            'action': 'remixed',
            'token': util.token(user.id),
            'user_id': user.id,
        })

        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))
        self.assertStatus(200, url, user=AnonymousUser())
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))

    def test_email_token_that_corresponds_to_user_allows_from_channel(self):
        user = create_user()
        url = "/unsubscribe?" + urllib.urlencode({
            'action': 'remixed',
            'token': util.token(user.email),
            'email': user.email,
        })

        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))
        self.assertStatus(200, url, user=AnonymousUser())
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))

    def test_email_token_allows_unsubscribe_from_all(self):
        email = "foo@example.com"
        url = "/unsubscribe?" + urllib.urlencode({
            'token': util.token(email),
            'email': email,
        })

        self.assertFalse(EmailUnsubscribe.objects.get_or_none(email=email))
        self.assertStatus(200, url, user=AnonymousUser())
        self.assertTrue(EmailUnsubscribe.objects.get_or_none(email=email))

    def test_broken_token_ignored_for_logged_in_user(self):
        user = create_user()
        url = "/unsubscribe?" + urllib.urlencode({
            'action': 'remixed',
            'token': "GARBAGE DAY",
            'email': user.email,
        })

        self.assertTrue(user.kv.subscriptions.can_receive('remixed'))
        self.assertStatus(200, url, user=user)
        self.assertFalse(user.kv.subscriptions.can_receive('remixed'))

    def test_unsubscribe_page_without_user_id(self):
        user = create_user()
        resp = self.get('/unsubscribe?' + urllib.urlencode({
            'token': util.token(user.email),
            'email': user.email,
        }))
        self.assertNumCssMatches(0, resp, 'input[name="user_id"]')

    def test_unsubscribe_page_with_user_id(self):
        user = create_user()
        resp = self.get('/unsubscribe?' + urllib.urlencode({
            'token': util.token(user.email),
            'email': user.email,
            'user_id': user.id,
        }))
        selector = 'input[name="user_id"]'
        self.assertNumCssMatches(1, resp, 'input[name="user_id"]')

    def test_granular_unsubscribe(self):
        all_actions = EmailChannel.all_handled_actions()

        for action in all_actions:
            if action == 'newsletter':
                continue
            u = create_user()
            assert u.kv.subscriptions.can_receive(action)
            actions_dict = {}
            actions_dict = {action: "on"}
            self.validate_unsubscript(actions_dict, u)
            assert u.kv.subscriptions.can_receive(action)

    def test_unsubscribe_headers(self):
        action = 'remixed'
        user = create_user()
        self.assertTrue(user.kv.subscriptions.can_receive(action, EmailChannel))
        self.assertStatus(200, "/unsubscribe?action="+action, user=user)
        self.assertFalse(user.kv.subscriptions.can_receive(action, EmailChannel))

    def test_granualr_unsubscribe_blanket_ban(self):
        all_actions = EmailChannel.all_handled_actions()
        # ALL has inverted semantics ... make sure it works.
        all_actions.append("ALL")
        # Reuse the same user
        canvas_user = create_user()
        action = "ALL"
        actions_dict = {action: "on"}
        unsubscriptions = self.validate_unsubscript(actions_dict, canvas_user, all_actions)
        for action in all_actions:
            # Ensure that we unsubscribed from all of them!
            assert unsubscriptions.get(action)

        action = "ALL"
        # Remove blanket subscription
        actions_dict = {}
        request = FakeRequest()
        views.handle_unsubscribe_post(canvas_user, actions_dict, request)
        unsubscriptions = views.get_unsubscriptions(canvas_user, all_actions)
        for action in all_actions:
            # Ensure that the user is now subscribed for everything, which is the default without the blanket ban.
            assert not unsubscriptions.get(action)

    def validate_unsubscript(self, actions_dict, canvas_user=None, all_actions=None):
        if not canvas_user:
            canvas_user = create_user()
        if not all_actions:
            all_actions = EmailChannel.all_handled_actions()

        request = FakeRequest()
        views.handle_unsubscribe_post(canvas_user, actions_dict, request)
        unsubscriptions = views.get_unsubscriptions(canvas_user, all_actions)
        for action in all_actions:
            if action == 'newsletter':
                continue
            value = action
            if action == "ALL":
                value = not action
            if actions_dict.get(action) == "on":
                assert not unsubscriptions.get(value)
            else:
                assert unsubscriptions.get(value)
        return unsubscriptions


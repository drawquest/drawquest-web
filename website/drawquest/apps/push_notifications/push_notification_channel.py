# -*- coding: utf-8 -*-
from django.utils import translation
from django.utils.translation import ugettext, ugettext_lazy as _, pgettext_lazy
from django.utils.encoding import force_text

from apps.activity import jinja_tags
from canvas.notifications.base_channel import CommunicationsChannel
from drawquest.apps.push_notifications import models


class PushNotificationChannel(CommunicationsChannel):
    recipient_actions = [
        'quest_of_the_day',
        'facebook_friend_joined',
        'twitter_friend_joined',
        'followed_by_user',
        'starred',
    ]

    @classmethod
    def enabled_for_recipient_action(cls, action, recipient, pending_notification=None, *args, **kwargs):
        flag = super(PushNotificationChannel, cls).enabled_for_recipient_action(
            action, recipient, pending_notification=pending_notification, *args, **kwargs)

        try:
            return flag and not models.is_unsubscribed(recipient, action)
        except ValueError:
            return flag

    def _push(self, notification, alert, extra_metadata={}, badge=None):
        language_code = notification.recipient.kv.last_language_code.get() or 'en'
        translation.activate(language_code)
        localized_alert = force_text(alert)
        translation.deactivate()

        recipient = notification.recipient
        models.push_notification(notification.action, localized_alert,
                                 recipient=recipient, extra_metadata=extra_metadata, badge=badge)

    def _action_facebook_friend_joined(self, notification):
        self._push(notification, _(u"%(first_name)s %(last_name)s joined DrawQuest as \"%(username)s\"" % {
            'first_name': notification.actor.facebookuser.first_name,
            'last_name': notification.actor.facebookuser.last_name,
            'username': notification.actor.username}),
            extra_metadata={'username': notification.actor.username})

    def _action_twitter_friend_joined(self, notification):
        twitter_user = notification.actor.twitteruser
        self._push(notification, _(u"%(name)s (@%(screen_name)s) joined DrawQuest as \"%(username)s\"" % {
            'name': twitter_user.name,
            'screen_name': twitter_user.screen_name,
            'username': notification.actor.username}),
            extra_metadata={'username': notification.actor.username})

    def _action_starred(self, notification):
        self._push(notification, _(u"%(username)s starred your drawing" % {'username': notification.actor.username}),
            extra_metadata={
                'comment_id': notification.comment_sticker.comment.id,
                'quest_id': notification.comment_sticker.comment.parent_comment_id,
            })

    def _action_featured_in_explore(self, notification):
        self._push(notification, _("Congrats—you're featured in Explore and received 10 coins!"),
                   extra_metadata={'comment_id': notification.comment.id})

    def _action_followed_by_user(self, notification):
        self._push(notification, _(u"%(username)s started following you" % {'username': notification.actor.username}),
                   extra_metadata={'username': notification.actor.username})

    def deliver(self, notification):
        getattr(self, '_action_' + notification.action)(notification)


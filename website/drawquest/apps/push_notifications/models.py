from urbanairship import Airship, AirshipFailure
from django.utils import translation
from django.utils.encoding import force_text
from django.conf import settings

from canvas import util
from canvas.metrics import Metrics
from canvas.redis_models import RedisSet


GLOBAL_PUSH_NOTIFICATION_TYPES = {
    'quest_of_the_day':         0,
}

PERSONAL_PUSH_NOTIFICATION_TYPES = {
    'starred':                  2,
    'facebook_friend_joined':   3,
    'featured_in_explore':      4,
    'twitter_friend_joined':    5,
    'followed_by_user':         6,
}

def push_notification(notification_type, alert, extra_metadata={}, recipient=None, badge=None, request=None):
    """
    `recipient` is a User instance.
    """
    # ### DISABLED ###
    return

    ua = Airship(settings.URBANAIRSHIP_APP_KEY, settings.URBANAIRSHIP_APP_MASTER_SECRET)

    def payload_for_language(language_code):
        try:
            translation.activate(language_code)
        except AttributeError:
            translation.activate('en')
            localized_alert = force_text(alert)
        else:
            localized_alert = force_text(alert)
        finally:
            translation.deactivate()

        _payload = {'aps': {'alert': localized_alert}, 'push_notification_type': notification_type}
        _payload.update(extra_metadata)

        if badge is not None:
            _payload['aps']['badge'] = badge

        return _payload

    payload = payload_for_language('en')

    if notification_type in GLOBAL_PUSH_NOTIFICATION_TYPES:
        if settings.PRODUCTION or settings.STAGING:
            ua.push(payload, tags=[notification_type])

            for locale in settings.ALL_LOCALES:
                localized_payload = payload_for_language(locale)

                ua.push(localized_payload, tags=['{}-{}'.format(notification_type, locale)])

            util.logger.info(u"Sent global push notification with alert: {}".format(alert))
    elif notification_type in PERSONAL_PUSH_NOTIFICATION_TYPES:
        if (settings.PRODUCTION or settings.STAGING) and not is_unsubscribed(recipient, notification_type):
            try:
                ua.push(payload, aliases=[recipient.username])
            except AirshipFailure:
                # UA frequently errors out. Retry.
                try:
                    ua.push(payload, aliases=[recipient.username])
                except AirshipFailure:
                    pass
    else:
        raise ValueError("Invalid push notification type '{}'.".format(notification_type))


# Subscriptions only matter for personal notifications. Global notification subscriptions are handled on the device.

unsubscriptions = dict((name, RedisSet('push_notification:{0}:unsubscriptions'.format(id_)),)
                       for name, id_ in PERSONAL_PUSH_NOTIFICATION_TYPES.items())

def _check_personal_type(push_notification_type):
    if push_notification_type not in PERSONAL_PUSH_NOTIFICATION_TYPES:
        raise ValueError("Invalid personal push notification type '{}'".format(push_notification_type))

def unsubscribe(user, push_notification_type):
    _check_personal_type(push_notification_type)
    unsubscriptions[push_notification_type].sadd(user.id)

def resubscribe(user, push_notification_type):
    _check_personal_type(push_notification_type)
    unsubscriptions[push_notification_type].srem(user.id)

def unsubscribers(push_notification_type):
    _check_personal_type(push_notification_type)
    return unsubscriptions[push_notification_type].smembers()

def is_unsubscribed(user, push_notification_type):
    _check_personal_type(push_notification_type)
    return str(user.id) in unsubscriptions[push_notification_type]

def is_subscribed(user, push_notification_type):
    return not is_unsubscribed(user, push_notification_type)


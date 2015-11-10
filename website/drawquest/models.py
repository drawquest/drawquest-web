from datetime import datetime, timedelta as td
from string import swapcase

from cachecow.decorators import cached_function
from django.conf import settings
from django.db.models.signals import post_save
from django.shortcuts import get_object_or_404, Http404
from django.utils.translation import ugettext, ugettext_lazy as _, pgettext_lazy

from canvas.exceptions import ResponseTooLarge
from canvas.models import UserInfo, FacebookUser, Visibility
from canvas.redis_models import RealtimeChannel, redis
from canvas.util import parse_version
from drawquest import knobs, economy
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.feed.redis_models import has_new_feed_comments
from drawquest.apps.following import models as following_models
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import current_quest_details, completed_quest_ids, Quest, has_new_inbox_items, ScheduledQuest
from drawquest.apps.twitter.models import TwitterUser
from website.apps.activity.models import activity_stream_items
from website.apps.canvas_auth.models import User as CanvasUser


@cached_function(timeout=td(days=14), key=[
    ['user_profile', 'v6'],
    lambda username: username,
])
def user_profile(username):
    user = get_object_or_404(User.objects.select_related('userinfo', 'userinfo__avatar'), username=username)

    if not user.is_active:
        raise Http404("Deactivated user.")

    follow_counts = following_models.counts(user)

    ret = {
        'user': user.details(),
        'bio': user.userinfo.bio_text,
        'quest_completion_count': Quest.completed_by_user_count(user),
        'follower_count': follow_counts['followers'],
        'following_count': follow_counts['following'],
    }

    if not user.kv.web_profile_privacy.get():
        ret['web_profile_url'] = 'https://{}/{}'.format(settings.DOMAIN, user.username)

    for service, attr in [('facebook', 'fb_uid'), ('twitter', 'screen_name')]:
        try:
            privacy_kv = lambda: getattr(user.kv, '{}_privacy'.format(service))
            service_user = getattr(user, '{}user'.format(service))
            private = privacy_kv().get()

            # Migrate users from before this feature was added.
            if private is None:
                privacy_kv().set(False)
                private = False

            if not private:
                ret['{}_url'.format(service)] = 'https://{}.com/{}'.format(service, getattr(service_user, attr))
        except (FacebookUser.DoesNotExist, TwitterUser.DoesNotExist,):
            pass

    return ret

# Cache invalidation for user_profile.
post_save.connect(
    lambda sender, instance, **kwargs: user_profile.delete_cache(instance.username),
    sender=CanvasUser, dispatch_uid='post_save_for_user_profile_canvas_user', weak=False
)
post_save.connect(
    lambda sender, instance, **kwargs: user_profile.delete_cache(instance.username),
    sender=User, dispatch_uid='post_save_for_user_profile_user', weak=False
)
post_save.connect(
    lambda sender, instance, **kwargs: user_profile.delete_cache(instance.user.username),
    sender=UserInfo, dispatch_uid='post_save_for_user_profile_userinfo', weak=False
)
post_save.connect(
    lambda sender, instance, **kwargs: user_profile.delete_cache(instance.author.username),
    sender=QuestComment, dispatch_uid='post_save_for_completed_quest_ids_user_profile', weak=False
)

def user_profile_for_viewer(username, viewer=None):
    ret = user_profile(username)
    user = get_object_or_404(User, username=username)

    if viewer and viewer.is_authenticated() and viewer.username != user.username:
        if user.username.lower() == 'questbot':
            ret.update({
                'viewer_is_following': viewer.is_following(user),
                'comment_count': 0,
                'quest_count': ScheduledQuest.archived().count(),
            })
        else:
            #TODO use the new comment_count method on user objs here
            ret.update({
                'viewer_is_following': viewer.is_following(user),
                'comment_count': QuestComment.objects.filter(author=user, visibility=Visibility.PUBLIC).count(),
                'quest_count': Quest.objects.filter(author=user, visibility=Visibility.PUBLIC).count(),
            })
    else:
        #TODO use the new comment_count method on user objs here
        ret.update({
            'comment_count': QuestComment.objects.filter(author=user, visibility__in=[Visibility.PUBLIC, Visibility.CURATED]).count(),
            'quest_count': Quest.objects.filter(author=user, visibility__in=[Visibility.PUBLIC, Visibility.CURATED]).count(),
        })

    return ret

def realtime_sync(user):
    channel_ids = ['qotd']

    if user.is_authenticated():
        channel_ids.append(user.redis.activity_stream_channel.channel)
        channel_ids.append(user.redis.coin_channel.channel)
        channel_ids.append(user.redis.tab_badges_channel.channel)

    channels = {}
    for channel_id in channel_ids:
        channel = RealtimeChannel(channel_id)
        channels[channel_id] = channel.sync()

    return channels

def heavy_state_sync(user, app_version=None, app_version_tuple=None, tab_last_seen_timestamps={}):
    from drawquest.apps.brushes.models import Brush
    from drawquest.apps.palettes.models import user_palettes, Color

    twitter_keys = '{}@{}'.format(settings.TWITTER_APP_KEY , settings.TWITTER_APP_SECRET)
    twitter_keys = twitter_keys[-6:] + twitter_keys[:-6]
    twitter_keys = swapcase(twitter_keys)

    ret = {
        'realtime_sync': realtime_sync(user),
        'user_palettes': user_palettes(user),
        'current_quest': current_quest_details(),
        'onboarding_quest_id': knobs.ONBOARDING_QUEST_ID,
        'sync': twitter_keys,
        'tumblr_success_regex': '''<div style="margin-bottom:10px; font-size:40px; color:#777;">Done!</div>''',
        'rewards': {
            'amounts': knobs.REWARDS,
            'copy': {
                'quest_of_the_day': _("You drew the Quest of the Day"),
                'archived_quest':   _("You drew a Quest"),
                'first_quest':      _("Woo! Your first Quest ever!"),
                'streak_3':         _("Quest Streak: 3"),
                'streak_10':        _("Quest Streak: 10"),
                'streak_100':       _("Epic! 100 straight Quests"),
            },
            'iphone_copy': {
                'archived_quest': _("You drew a Quest"),
                'first_quest': _("Your first Quest!"),
                'quest_of_the_day': _("Quest of the Day!"),
                'streak_10': _("Bonus Streak"),
                'streak_100': _("Bonus Streak"),
                'streak_3': _("Bonus Streak"),
                'personal_share': _("Shared with Facebook"),
                'personal_twitter_share': _("Shared with Twitter"),
            },
        },
        'features': {
            'invite_from_facebook': True,
            'invite_from_twitter': True,
            'user_search': True,
            'urban_airship_registration_before_auth': True,
            'urban_airship_registration': True,
        },
        'logging': {
            'on': True,
            'authentication-controller': {
                'request-for-me': False,
            },
            'facebook-controller': {
                'open-active-session-with-read-permissions': False,
                'request-new-publish-permissions': False,
                'request-new-publish-permissions-cancelled': False,
                'request-new-read-permissions': False,
                'request-new-read-permissions-cancelled': False,
            },
            'facebook-friends-coordinator': {
                'present-requests-dialog': False,
                'request-my-friends': False,
            },
            'http-request': {
                'error-auth/login_with_facebook': {
                    'mute-error-codes': {
                        '403': True,
                    }
                },
                'error-auth/login_with_twitter': {
                    'mute-error-codes': {
                        '403': True,
                    }
                },
                'error-quests/gallery_for_comment': {
                    'mute-error-codes': {
                        '404': True,
                    }
                }
            },
            'private-api': {
                'failed-activity/iphone_activities': {
                    'mute-error-codes': {
                        '1005': True,
                    }
                }
            },
            'sharing-controller': {
                'present-feed-dialog': False,
                'present-share-dialog-with-link': False,
            },
            'shop-controller': {
                'add-payment': False,
                'brush-products-request': False,
                'coin-products-request': False,
            },
            'twitter-api-manager': {
                'step-1': False,
                'step-2': False,
            },
            'twitter-controller': {
                'request-data-cursored-user-ids': False,
                'request-data-send-dm': False,
                'request-data-unknown': False,
                'request-data-users-for-ids': False,
            },
        },
        #TODO use settings.LOCALES once that's ready
        'supported_languages': ['de', 'en', 'es', 'fr', 'ja', 'ko', 'nl', 'pt', 'ru', 'th', 'zh-Hant', 'zh-Hans'],
        'l10n_files_url': None,
        'user_colors': list(Color.for_user(user)),
        'user_brushes': list(Brush.for_user(user)),
        'global_brushes': list(Brush.for_global()),
        'comment_view_logging_interval': 10,
        'papertrail': {
            'host': 'logs.papertrailapp.com',
            'port': 27889,
            'disabled_logging_points': [],
        },
        'modals': {},
    }

    if app_version_tuple and app_version_tuple >= (3,):
        ret['appirater_url'] = 'itms-apps://itunes.apple.com/app/idAPP_ID'
    else:
        ret['appirater_url'] = 'itms-apps://ax.itunes.apple.com/WebObjects/MZStore.woa/wa/viewContentsUserReviews?type=Purple+Software&id=APP_ID'

    try:
        ret['color_alert_version'] = int(redis.get('color_alert_version'))
    except TypeError:
        ret['color_alert_version'] = 0

    if user.is_authenticated():
        user_kv_items = user.kv.hgetall()
        user_kv_items = dict((key, val) for key, val in user_kv_items.items()
                             if key in [
                                 'saw_update_modal_for_version',
                                 'saw_share_web_profile_modal',
                                 'publish_to_facebook',
                                 'publish_to_twitter',
                             ])

        ret.update({
            'user_email': user.email,
            'user_profile': user_profile(user.username),
            'balance': economy.balance(user),
            'completed_quest_ids': completed_quest_ids(user),
            'web_profile_privacy': user.kv.web_profile_privacy.get(),
            'twitter_privacy': user.kv.twitter_privacy.get(),
            'facebook_privacy': user.kv.facebook_privacy.get(),
            'user_kv': user_kv_items,
            'reminders': {
                'invite': 1,
            },
        })

        if (app_version and parse_version(knobs.CURRENT_APP_VERSION) > parse_version(app_version)):
            saw_version = user_kv_items.get('saw_update_modal_for_version')
            if (saw_version is None
                    or parse_version(saw_version) < parse_version(knobs.CURRENT_APP_VERSION)):
                ret['modals']['show_update_modal_for_version'] = knobs.CURRENT_APP_VERSION
                ret['modals']['update_modal_type'] = 'alert'

        if not user_kv_items.get('saw_share_web_profile_modal'):
            ret['modals']['show_share_web_profile_modal'] = (user.date_joined <= (datetime.now() - td(days=2))
                                                             or user.comments.count() >= 3)

    ret['tab_badge_type'] = 'flag'
    if tab_last_seen_timestamps:
        ret['tab_badges'] = tab_badges(user, last_seen_timestamps=tab_last_seen_timestamps)

    return ret

def tab_badges(user, last_seen_timestamps={}):
    tabs = {'home': False, 'draw': False, 'activity': False}

    if not user.is_authenticated():
        return tabs

    if last_seen_timestamps.get('home'):
        tabs['home'] = has_new_feed_comments(user, last_seen_timestamps['home'])
    
    if last_seen_timestamps.get('draw'):
        tabs['draw'] = has_new_inbox_items(user, last_seen_timestamps['draw'])

    if last_seen_timestamps.get('activity'):
        try:
            tabs['activity'] = len(activity_stream_items(user, later_than=last_seen_timestamps['activity'], iphone=True)) > 0
        except ResponseTooLarge:
            tabs['activity'] = True

    return tabs


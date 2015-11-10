from datetime import datetime, timedelta

from django.conf import settings
from django.conf.urls import url, patterns, include
from django.contrib.auth.forms import PasswordChangeForm
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext, ugettext_lazy as _, pgettext, pgettext_lazy

from canvas.exceptions import ServiceError, ValidationError
from canvas.models import Content, UserInfo
from canvas.redis_models import redis
from canvas.upload import api_upload, chunk_uploads
from canvas.view_guards import require_staff, require_POST, require_user
from drawquest import signals, models, api_forms, economy
from drawquest.api_decorators import api_decorator
from drawquest.apps.brushes.models import Brush
from drawquest.apps.drawquest_auth.details_models import PrivateUserDetails
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.iap.models import COIN_PRODUCTS, brush_products
from drawquest.apps.palettes.models import Color, ColorPack
from drawquest.apps.twitter.models import TwitterUser
from drawquest.apps.quests.models import Quest
from drawquest.apps.quest_comments.models import QuestComment
from website.apps.share_tracking.models import ShareTrackingUrl, get_share_page_url_with_tracking


urls = patterns('',
    url(r'^quest_comments/flag', 'apps.comments.api.flag_comment'),
    url(r'^quests/flag', 'apps.comments.api.flag_comment'),
)

urls += patterns('drawquest.api',
    url(r'^activity/', include('apps.activity.api')),
    url(r'^auth/', include('drawquest.apps.drawquest_auth.api')),
    url(r'^brushes/', include('drawquest.apps.brushes.api')),
    url(r'^chunk/', include(chunk_uploads)),
    url(r'^explore/', include('drawquest.apps.explore.api')),
    url(r'^feed/', include('drawquest.apps.feed.api')),
    url(r'^following/', include('drawquest.apps.following.api')),
    url(r'^iap/', include('drawquest.apps.iap.api')),
    url(r'^ios_logging/', include('drawquest.apps.ios_logging.api')),
    url(r'^invites/', include('drawquest.apps.invites.api')),
    url(r'^palettes/', include('drawquest.apps.palettes.api')),
    url(r'^playback/', include('drawquest.apps.playback.api')),
    url(r'^push_notifications/', include('drawquest.apps.push_notifications.api')),
    url(r'^quest_comments/', include('drawquest.apps.quest_comments.api')),
    url(r'^quest_comments/', include('drawquest.apps.star_gallery.api')),
    url(r'^quest_invites/', include('drawquest.apps.quest_invites.api')),
    url(r'^quests/', include('drawquest.apps.gallery.api')),
    url(r'^quests/', include('drawquest.apps.quests.api')),
    url(r'^profiles/', include('drawquest.apps.profiles.api')),
    url(r'^stars/', include('drawquest.apps.stars.api')),
    url(r'^submit_quest/', include('drawquest.apps.submit_quest.api')),
    url(r'^staff/', include('drawquest.apps.staff.api')),
    url(r'^timeline/', include('drawquest.apps.timeline.api')),
    url(r'^tumblr/', include('drawquest.apps.tumblr.api')),
    url(r'^ugq/', include('drawquest.apps.ugq.api')),
    url(r'^upload$', api_upload),
    url(r'^whitelisting/', include('drawquest.apps.whitelisting.api')),

    # Only used for the admin.
    url(r'^comment/', include('apps.comments.api')),

    # Disabled for now for perf.
    #url(r'^', include('apps.analytics.api')),
)

if settings.DRAWQUEST_SEARCH:
    urls += patterns('drawquest.api',
        url(r'^search/', include('drawquest.apps.search.api')),
    )

api = api_decorator(urls)

@api('metric/record')
def metric_record(request, name, info={}):
    """ Currently a no-op. """

@api('user/profile')
def user_profile(request, username):
    return models.user_profile_for_viewer(username, viewer=request.user)

@api('user/change_profile')
@require_user
def change_profile(request, old_password=None, new_password=None, new_email=None, bio=None):
    if bio is not None:
        request.user.userinfo.bio_text = bio
        request.user.userinfo.save()
        request.user.details.force()

    if new_email is not None:
        if not User.validate_email(new_email):
            raise ValidationError({'new_email': "Please enter a valid email address."})

        if request.user.email != new_email:
            if not User.email_is_unused(new_email):
                raise ValidationError({
                    'new_email': "Sorry! That email address is already being used for an account.",
                })

            request.user.email = new_email
            request.user.save()
            request.user.userinfo.update_hashes()
            request.user.details.force()

    if old_password is not None and new_password is not None:
        if not User.validate_password(new_password):
            raise ValidationError({
                'new_password': "Sorry, your new password is too short. "
                                "Please use {} or more characters.".format(User.MINIMUM_PASSWORD_LENGTH),
            })

        form = PasswordChangeForm(user=request.user, data={
            'old_password': old_password,
            'new_password1': new_password,
            'new_password2': new_password,
        })

        api_forms.validate(form)
        form.save()
        request.user.details.force()

@api('user/change_avatar')
@require_user
def change_avatar(request, content_id):
    user_info = request.user.userinfo
    user_info.avatar = get_object_or_404(Content, id=content_id)
    user_info.save()

    user = User.objects.get(id=request.user.id)
    user.invalidate_details()

# DEPRECATED.
@api('create_email_invite_url')
def create_email_invite_url(request):
    url = 'http://example.com/download'

    if request.user.is_authenticated():
        sharer = request.user
        share = ShareTrackingUrl.create(sharer, url, 'email')
        url = share.url_for_channel()

    return {'invite_url': url}

@api('existing_users_by_email')
def existing_users_by_email(request, email_hashes):
    uis = UserInfo.objects.filter(email_hash__in=email_hashes)

    if request.user.is_authenticated():
        uis = uis.exclude(user=request.user)

    uis = uis.select_related('user')
    uis = uis.values_list('user__email', 'user__username', 'user__id')

    following = None
    if request.user.is_authenticated():
        following = [int(id_) for id_ in request.user.redis.new_following.zrange(0, -1)]

    users = []

    for ui in uis:
        user = {'email': ui[0], 'username': ui[1]}

        if following is not None:
            user['viewer_is_following'] = ui[2] in following

        users.append(user)

    return {'users': users}

@api('realtime/sync')
def realtime_sync(request):
    return {'channels': models.realtime_sync(request.user)}

@api('share/create_for_channel')
def share_create_for_channel(request, channel, comment_id=None, quest_id=None, download_link=False, is_invite=False):
    ret = {}

    def download_share():
        return ShareTrackingUrl.create(request.user, 'http://example.com/download', channel)

    if not download_link and comment_id is not None and quest_id is not None:
        raise ValueError("Can't specify both a comment and quest to share.")

    if download_link:
        return {'share_url': download_share().url_for_channel()}

    if is_invite:
        if quest_id is None:
            share_url = download_share().url_for_channel()

            if channel == 'twitter':
                message = _(u"Come draw with me on @DrawQuest! %(url)s" % {'url': share_url})
            elif channel == 'email':
                follow_me_message = _("You can follow me in the app as \"%(username)s\"" % {'username': getattr(request.user, 'username')}) if request.user.is_authenticated() else ''
                message = _(u"""I'm using DrawQuest, a free creative drawing app for iPhone, iPod touch, and iPad. DrawQuest sends you daily drawing challenges and allows you to create your own to share with friends. %(follow_me_message)s

Download DrawQuest for free here: %(url)s""" % {'follow_me_message': follow_me_message, 'url': share_url})
            else:
                message = _(u"Come draw with me on DrawQuest! %(url)s" % {'url': share_url})
        else:
            quest = get_object_or_404(Quest, id=quest_id)

            if channel in ['twitter', 'facebook']:
                share_url = get_share_page_url_with_tracking(quest, request.user, channel, request=request)
            else:
                share_url = download_share().url_for_channel()

            if request.user.is_authenticated() and quest.author_id == request.user.id:
                if channel == 'twitter':
                    message = _(u"I just created a Quest on @DrawQuest! \"%(quest_title)s\" Come draw it with me: %(url)s" % {'quest_title': quest.title, 'url': share_url})
                else:
                    message = _(u"I just created a Quest on DrawQuest! \"%(quest_title)s\" Come draw it with me: %(url)s" % {'quest_title': quest.title, 'url': share_url})
            else:
                if channel == 'twitter':
                    message = _(u"Come draw \"%(quest_title)s\" with me on @DrawQuest! %(url)s" % {'quest_title': quest.title, 'url': share_url})
                else:
                    message = _(u"Come draw \"%(quest_title)s\" with me on DrawQuest! %(url)s" % {'quest_title': quest.title, 'url': share_url})

        return {
            'share_url': share_url,
            'message': message,
        }

    if comment_id is None and quest_id is None:
        share = ShareTrackingUrl.create(request.user, None, channel)
        ret['share_id'] = share.id
        url = share.url_for_channel()
    else:
        if quest_id is not None:
            shared_obj = get_object_or_404(Quest, id=quest_id)
            quest_title = shared_obj.title
        else:
            shared_obj = get_object_or_404(QuestComment, id=comment_id)
            quest_title = shared_obj.parent_comment.title

        author = User.objects.get(id=shared_obj.author_id)

        if channel in ['twitter', 'facebook']:
            url = get_share_page_url_with_tracking(shared_obj, request.user, channel, request=request)
        else:
            url = download_share().url_for_channel()

        if channel == 'twitter':
            if quest_id is not None:
                ret['tweet'] = _(u'Come draw "%(quest_title)s" with me on @DrawQuest! %(url)s' % {'quest_title': quest_title, 'url': url})
            else:
                ret['tweet'] = _(u'"%(quest_title)s" %(url)s via @DrawQuest' % {'quest_title': quest_title, 'url': url})

            if author.kv.twitter_privacy.get() == False:
                try:
                    author_screen_name = ret['twitter_screen_name'] = author.twitteruser.screen_name
                    if quest_id is not None:
                        ret['tweet'] = _(u'Come draw "%(quest_title)s" by @%(screen_name)s with me on @DrawQuest! %(url)s' % {'quest_title': quest_title, 'url': url, 'screen_name': author_screen_name})
                    else:
                        ret['tweet'] = _(u'"%(quest_title)s" %(url)s by @%(screen_name)s via @DrawQuest' % {'quest_title': quest_title, 'url': url, 'screen_name': author_screen_name})
                except (AttributeError, TwitterUser.DoesNotExist):
                    pass

            ret['message'] = ret['tweet']
        elif channel == 'email':
            if quest_id is not None:
                ret['message'] = _(u"""I'm using DrawQuest, a free creative drawing app for iPhone, iPod touch, and iPad. DrawQuest sends you daily drawing challenges and allows you to create your own to share with friends. I thought you might enjoy this Quest: \"%(quest_title)s\"

Download DrawQuest for free here: %(url)s""" % {'quest_title': quest_title, 'url': url})
            else:
                ret['message'] = _(u"""I thought you'd like this drawing made with DrawQuest, a free creative drawing app for iPhone, iPod touch, and iPad.

\"%(quest_title)s\" %(url)s

Download DrawQuest for free here: %(download_url)s""" % {'quest_title': quest_title, 'url': get_share_page_url_with_tracking(shared_obj, request.user, channel, request=request), 'download_url': url})
        else:
            if quest_id is not None:
                ret['message'] = _(u"Come draw \"%(quest_title)s\" with me on DrawQuest! %(url)s" % {'quest_title': quest_title, 'url': url})
            else:
                if channel == 'text_message':
                    ret['message'] = _(u"""Check out this drawing on DrawQuest: \"%(quest_title)s\" %(url)s

Download DrawQuest for free here: %(download_url)s""" % {'quest_title': quest_title, 'url': get_share_page_url_with_tracking(shared_obj, request.user, channel, request=request), 'download_url': url})
                else:
                    ret['message'] = _(u"Check out this drawing on DrawQuest: \"%(quest_title)s\" %(url)s" % {'quest_title': quest_title, 'url': url})

    if channel == 'facebook':
        url = 'http://example.com' + url

    if not ret.get('message'):
        if channel == 'twitter':
            ret['message'] = _(u"Come draw with me on @DrawQuest! %(url)s" % {'url': url})
        else:
            ret['message'] = _(u"Come draw with me on DrawQuest! %(url)s" % {'url': url})

    ret['share_url'] = url

    return ret

@api('economy/balance')
@require_user
def coin_balance(request):
    return {'balance': economy.balance(request.user)}

@api('user/set_web_profile_privacy')
@require_user
def set_web_profile_privacy(request, privacy):
    request.user.kv.web_profile_privacy.set(privacy)
    models.user_profile.delete_cache(request.user.username)

@api('user/set_twitter_privacy')
@require_user
def set_twitter_privacy(request, privacy):
    request.user.kv.twitter_privacy.set(privacy)
    models.user_profile.delete_cache(request.user.username)

@api('user/set_facebook_privacy')
@require_user
def set_facebook_privacy(request, privacy):
    request.user.kv.facebook_privacy.set(privacy)
    models.user_profile.delete_cache(request.user.username)

@api('kv/set')
@require_user
def kv_set(request, items):
    for key in items.keys():
        if key not in request.user.kv.DEFINITION.keys():
            raise AttributeError(key)

    for key, val in items.items():
        request.user.kv.set(key, val)

@api('heavy_state_sync')
def heavy_state_sync(request, tab_last_seen_timestamps={}):
    return models.heavy_state_sync(request.user, app_version=request.app_version, app_version_tuple=request.app_version_tuple, tab_last_seen_timestamps=tab_last_seen_timestamps)

@api('shop/all_items')
@require_user
def shop_all_items(request):
    ret = {
        'shop_brushes': Brush.for_shop(viewer=request.user, request=request),
        'shop_colors': Color.for_shop(viewer=request.user),
        'color_packs': ColorPack.for_shop(viewer=request.user),
        'coin_products': COIN_PRODUCTS,
        'brush_products': brush_products(request=request),
        'balance': economy.balance(request.user),
        'color_packs_header': redis.get('color_packs_header'),
        'colors_header': redis.get('colors_header'),
        'tabs': [
            {'name': 'colors', 'default': True},
            {'name': 'coins'},
            {'name': 'brushes'},
        ],
    }

    return ret

@api('tab_badges')
def tab_badges(request, last_seen_timestamps={}):
    '''
    `last_seen_timestamps` looks like this:
        {'home': 1234567890, 'draw': 1234567890, 'activity': 1234567890}

    If a tab has never been seen yet, just omit it from the dict.

    Returns a dict like:
        {'home': True, 'draw': False, 'activity': True}
    '''
    return models.tab_badges(request.user, last_seen_timestamps=last_seen_timestamps)

@api('base_url')
def china_base_url(request):
    if settings.STAGING:
        return {
            'api_url': 'https://drawquestapi1.com/api/',
            'search_url': 'https://searchapi.example.com/',
            'web_url': 'https://drawquestapi1.com/',
            'rt_url': 'https://rt.example.com/rt',
        }
    else:
        from django.contrib.gis.geoip import GeoIP

        g = GeoIP()
        ip = request.META['REMOTE_ADDR']
        if ip and g.country_code(ip).upper() == 'CN':
            return {
                'api_url': 'https://drawquestapi1.com/api/',
                'search_url': 'https://searchapi.example.com/',
                'web_url': 'https://drawquestapi1.com/',
                'rt_url': 'https://rt.example.com/rt',
            }
        else:
            return {
                'api_url': 'https://api.example.com/',
                'search_url': 'https://searchapi.example.com/',
                'web_url': 'https://example.com/',
                'rt_url': 'https://rt.example.com/rt',
            }


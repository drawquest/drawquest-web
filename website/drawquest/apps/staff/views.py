import hashlib

from django.conf import settings
from django.db.models import Count
from django.shortcuts import get_object_or_404

from apps.activity.models import legacy_get_activity_stream_items
from canvas.util import parse_version
from canvas.models import Visibility, Content, FacebookUser, UserInfo
from drawquest.apps.twitter.models import TwitterUser
from canvas.redis_models import IP
from canvas.shortcuts import r2r_jinja
from canvas.util import int_to_ip, ip_to_int
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import Quest


def staff_stars(request):
    ctx = {
        'comments': QuestComment.objects.filter(
            stickers__user__is_staff=True,
        ).distinct().order_by('-id')
    }
    return r2r_jinja('staff/comments_grid.html', ctx, request)

def top_starred(request):
    ctx = {
        'comments': QuestComment.objects.order_by('-star_count')[:200],
    }
    return r2r_jinja('staff/comments_grid.html', ctx, request)

def deep_links(request):
    return r2r_jinja('staff/deep_links.html', {}, request)

def max_strokes(request, stroke_count):
    contents = Content.objects.filter(stroke_count__lte=stroke_count).exclude(stroke_count__isnull=True)
    contents = contents[:500]
    ctx = {
        'comments': [QuestComment.objects.get(id=content.first_caption.id) for content in contents],
    }
    return r2r_jinja('staff/comments_grid.html', ctx, request)

def user(request, username_or_email):
    try:
        user = User.objects.get(username=username_or_email)
    except User.DoesNotExist:
        try:
            user = User.objects.get(email=username_or_email)
        except User.DoesNotExist:
            ui = get_object_or_404(UserInfo, username_hash=username_or_email)
            user = User.objects.get(id=ui.user_id)

    ugq = Quest.all_objects.filter(author=user, ugq=True)
    cmts = QuestComment.all_objects.filter(author=user)

    ctx = {
        'examined_user': user,
        'username_hash': hashlib.sha1(user.username.encode('utf8')).hexdigest(),
        'public_ugq': ugq.filter(visibility=Visibility.PUBLIC),
        'disabled_ugq': ugq.filter(visibility=Visibility.DISABLED),
        'curated_ugq': ugq.filter(visibility=Visibility.CURATED),
        'public_comments': cmts.filter(visibility=Visibility.PUBLIC),
        'disabled_comments': cmts.filter(visibility=Visibility.DISABLED),
        'curated_comments': cmts.filter(visibility=Visibility.CURATED),
        'last_app_version': user.kv.last_app_version.get(),
    }

    try:
        ctx['signup_app_version'] = parse_version(user.kv.signup_app_version.get())
    except ValueError:
        ctx['signup_app_version'] = None

    try:
        ctx['facebook_user'] = user.facebookuser
    except FacebookUser.DoesNotExist:
        ctx['facebook_user'] = None

    try:
        ctx['twitter_user'] = user.twitteruser
    except TwitterUser.DoesNotExist:
        ctx['twitter_user'] = None

    return r2r_jinja('staff/user.html', ctx, request)

def user_activity_stream(request, username):
    user = User.objects.get(username=username)
    activities = legacy_get_activity_stream_items(user, count=450)
    ctx = {
        'examined_user': user,
        'activities': activities,
    }
    return r2r_jinja('staff/activity_stream.html', ctx, request)

def user_iap_receipts(request, username):
    user = User.objects.get(username=username)
    receipts = user.iap_receipts.all().order_by('-timestamp')
    ctx = {
        'examined_user': user,
        'receipts': receipts,
    }
    return r2r_jinja('staff/iap_receipts.html', ctx, request)

def user_ip_history(request, username):
    user = get_object_or_404(User, username=username)
    ip_history = [(int_to_ip(ip), timestamp) for (ip, timestamp) in user.redis.ip_history.with_scores[:]]
    ctx = {
        'target_user': user,
        'ip_history': ip_history,
    }
    return r2r_jinja('staff/ip_history.html', ctx, request)

def ip_user_history(request, ip):
    ip_int = ip_to_int(ip)
    history = IP(ip_int).user_history.with_scores[:]
    users = User.objects.in_bulk_list([user for (user, ts) in history])
    history = zip(users, [ts for (user, ts) in history])
    ctx = {
        'history': history,
    }
    return r2r_jinja('staff/user_history.html', ctx, request)


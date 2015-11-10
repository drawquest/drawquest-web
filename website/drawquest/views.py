import datetime
import time
from urllib import urlencode

from django.conf import settings
from django.core.mail import EmailMessage
from django.shortcuts import redirect

from canvas import util
from canvas.cache_patterns import cache_page
from canvas.metrics import Metrics
from canvas.models import unsubscribe_newsletter, CommentSticker
from canvas.notifications.email_channel import EmailChannel
from canvas.shortcuts import r2r_jinja
from canvas.subscriptions import get_unsubscriptions, handle_unsubscribe_post
from canvas.view_guards import require_staff, require_user
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.playback.models import Playback
from drawquest.apps.quests.models import Quest
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.forms import SupportForm


def homepage(request):
    if settings.DRAWQUEST_ADMIN:
        return redirect('/admin/staff')

    return r2r_jinja('drawquest/index.html', {}, request)

def unsubscribe(request):
    token = request.REQUEST.get('token', '')
    email = request.REQUEST.get('email')

    unsubscribe_all_link = 'http://{}/unsubscribe?'.format(settings.DOMAIN) + urlencode({
        'action': 'ALL',
        'token': util.token(email),
        'email': email,
    })

    ctx = {
        'token': token,
        'email': email,

        'unsubscribed': False,
        'unsubscribed_on_get': False,
        'unsubscribed_settings': None,
        'user': None,
        'error': False,
        'action': request.REQUEST.get('action'),
        'unsubscribe_all_link': unsubscribe_all_link,
    }

    template_name = 'unsubscribe.html'

    if email and util.token(email) == token:
        # No user_id associated with the sent email, unsubscribe this email address from all email
        find_user = User.objects.filter(email=email)
        # If there is one and only one user with that email address, then pick them, otherwise we'll fall back to just an email address
        user = ctx['unsubscribing_user'] = find_user[0] if find_user.count() == 1 else None
    else:
        ctx['error'] = True
        return r2r_jinja(template_name, ctx, request)

    all_actions = EmailChannel.all_handled_actions()

    if user:
        # Support for unsubscribe headers.
        # We support passing in 'actions'
        action = request.REQUEST.get('action')
        if action and (action in EmailChannel.all_handled_actions() or action.upper() == 'ALL'):
            ctx['unsubscribed_on_get'] = ctx['unsubscribed'] = True
            user.kv.subscriptions.unsubscribe(action)
            Metrics.unsubscribe_action.record(request, action=action, method=request.method)

        if request.method == 'POST':
            # Handle the 'ALL' case separately because the semantics for it are inverted.
            # ie, if ALL is checked, it means to DISABLE. While if REMIXED is checked, it means ENABLE.
            handle_unsubscribe_post(user, request.REQUEST, request)

        # We use this dictionary to render the checkboxes in the html.
        ctx['unsubscribed'] = ctx['unsubscribed'] or get_unsubscriptions(user, all_actions)

        ctx['unsubscribed_settings'] = get_unsubscriptions(user)
        template_name = 'unsubscribe_for_user.html'
    else:
        ctx['error'] = True
        return r2r_jinja(template_name, ctx, request)

    return r2r_jinja(template_name, ctx, request)

@require_staff
def vanity_metrics(request):
    def num(n):
        return '{:,}'.format(n)

    ctx = {
        'users': num(User.objects.filter(is_active=True).count()),
        'users_since_launch': num(User.objects.filter(is_active=True, date_joined__gte='2013-02-08').count()),
        'users_in_24h': num(User.objects.filter(is_active=True, date_joined__gte=datetime.datetime.now() - datetime.timedelta(days=1)).count()),
        'users_in_1h': num(User.objects.filter(is_active=True, date_joined__gte=datetime.datetime.now() - datetime.timedelta(hours=1)).count()),
        'iphone_drawings': num(QuestComment.published.filter(created_on_iphone=True).count()),
        'iphone_drawings_in_24h': num(QuestComment.published.filter(created_on_iphone=True, timestamp__gte=time.time() - (24*60*60)).count()),
        'drawings': num(QuestComment.published.count()),
        'drawings_in_24h': num(QuestComment.published.filter(timestamp__gte=time.time() - (24*60*60)).count()),
        'ugq': num(Quest.published.filter(ugq=True).count()),
        'ugq_in_24h': num(Quest.published.filter(ugq=True, timestamp__gte=time.time() - (24*60*60)).count()),
        'stars': num(CommentSticker.objects.filter(type_id=settings.STAR_STICKER_TYPE_ID).count()),
        'playbacks': num(Playback.objects.count()),
    }

    return r2r_jinja('staff/vanity_metrics.html', ctx, request)

def support(request):
    ctx = {}

    if request.method == 'POST':
        form = SupportForm(request.POST)
        if form.is_valid():
            subject = 'Support request from {}'.format(form.cleaned_data['username'])
            body = form.cleaned_data['message']

            mail = EmailMessage(subject, body, 'updates@example.com', ['appsupport@example.com'],
                      headers={'Reply-To': form.cleaned_data['sender']})
            mail.send()

            return r2r_jinja('drawquest/support_submitted.html', ctx, request)

        ctx['form'] = form
    else:
        form = SupportForm()
        ctx['form'] = form

    return r2r_jinja('drawquest/support.html', ctx, request)

def jinja_404(request):
    return r2r_jinja('404.html', {}, request, status=404)


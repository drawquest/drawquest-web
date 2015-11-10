import datetime
import itertools
import operator
import re
import string
import time
from random import choice

from django.contrib import auth
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, Http404, HttpResponse
from django.middleware import csrf
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from apps.canvas_auth.models import User
from apps.facebook_app.signed_request import authenticate
from apps.ip_blocking.view_guards import require_unblocked_ip
from apps.logged_out_homepage.views import homepage
from apps.signup.views import post_comment
from apps.tags.models import Tag
from canvas import browse, util, stickers, fact, after_signup
from canvas.browse import TileDetails
from canvas.date_util import days, days_ytd, hours, jstime_from_dt
from canvas.funnels import Funnels
from canvas.models import * #TODO delete
from canvas.notifications.email_channel import EmailChannel
from canvas.subscriptions import get_unsubscriptions, handle_unsubscribe_post
from canvas.redis_models import IP, gen_temp_key, redis
from canvas.shortcuts import r2r, r2r_jinja, direct_to_template
from canvas.util import make_absolute_url, int_to_ip, ip_to_int
from canvas.view_guards import require_staff, require_user, require_secure, require_POST
from canvas.view_helpers import (tile_render_options, redirect_trailing,
                                 top_url, top_timeperiod_urls, check_rate_limit, get_next)
from configuration import Config


def direct_to_django_template(request, template, **kwargs):
    return r2r('%s' % template, dict(kwargs, request=request))

def frontpage(request, sort, **kwargs):
    if request.user.is_authenticated() or request.is_mobile:
        return front_comments_view(request, sort, category=Category.get_default(request.user), **kwargs)
    else:
        return homepage(request)

@csrf_exempt
def facebook_welcome_page(request):
    return direct_to_django_template(request, "facebook_welcome_page.django.html")

#TODO: These four don't need views anymore
def code_of_conduct(request):
    return direct_to_template(request, "code_of_conduct.html")

def terms_of_service(request):
    return direct_to_template(request, "terms.html")

def privacy(request):
    return direct_to_template(request, "privacy.html")

def dmca(request):
    return direct_to_template(request, "dmca.html")

@require_user
def pinned(request):
    request.user.kv.pinned_unseen.set(0)
    response = frontpage(request, "pinned")
    # Set this after rendered so the templates have access to the old time.
    request.user.kv.pinned_lastviewed.set(Services.time.time())
    return response

@redirect_trailing
def category(request, name, sort, **kwargs):
    from apps.monster.models import MONSTER_GROUP

    category = Category.get(name=name)
    viewer_is_staff = request.user.is_authenticated() and request.user.is_staff
    if category is None:
        # Track this so that we can see the value in adding a "Group not found - want to create it?" page.
        Metrics.group_404.record(request)
        raise Http404()
    if isinstance(category, DisabledCategory):
        # Redirect to the category about page which will show the name, description, and a big red disabled message.
        return HttpResponseRedirect('/x/%s/about' % name)
    if category.name == MONSTER_GROUP and not viewer_is_staff:
        return HttpResponseRedirect('/monster')
    elif category.name in settings.HIDDEN_GROUPS and not viewer_is_staff:
        raise Http404()

    return front_comments_view(request, sort, category=category, **kwargs)

@redirect_trailing
def tag(request, tag, sort, **kwargs):
    if request.path.startswith('/t/'):
        return HttpResponseRedirect('/x/' + request.path[3:])
    if tag is None or (tag in settings.HIDDEN_GROUPS and not request.user.is_staff):
        raise Http404()
    if sort == 'top' and not kwargs.get('year'):
        today = datetime.date.today()
        kwargs['year'] = today.year
        kwargs['month'] = today.month
    if tag == "everything":
        return front_comments_view(request, sort, category=Category.get(name=tag), **kwargs)
    return front_comments_view(request, sort, tag=tag, **kwargs)

def front_comments_view(request, sort, category=None, tag=None, homepage=False, **kwargs):
    # category here should always be a first-class Category object.
    if not isinstance(category, CategoryMixin) and tag is None:
        raise Http404()

    user = request.user

    show_pins = request.user.is_authenticated()

    if not request.user.is_authenticated() and sort == 'hot' and category == Category.ALL:
        sort_type = request.GET.get('hot_sort_type', 'order_by_time_plus_log_stickers_and_replies')
        if sort_type != 'control':
            kwargs['hot_sort_type'] = sort_type

    kwargs['offset'] = request.GET.get('offset', 0)

    nav = browse.Navigation.load_json_or_404(
        kwargs,
        sort=sort,
        category=category,
        tag=tag,
        mobile=request.is_mobile,
    )

    front_data = {
        'tiles':          browse.get_browse_tiles(request.user, nav),
        'render_options': tile_render_options(sort, show_pins),
        'viewer_is_following_tag': tag and Tag(tag).user_is_following(request.user)
    }

    #TODO delete once we've resolved the missing small_image issue.
    for tile in front_data['tiles']:
        if hasattr(tile, 'check_for_small_image'):
            tile.check_for_small_image(request)

    # Overrides the default nav category that gets set in a context processor.
    if category is not None:
        request.nav_category = category

    if tag is not None:
        request.nav_tag = tag
        popular_tag_link = "/x/{}".format(tag)
        latest_tag_link = "/x/{}/new".format(tag)
        best_tag_link = "/x/{}/best".format(tag)
    else:
        popular_tag_link = "/x/everything"
        latest_tag_link = "/x/everything/new"
        best_tag_link = "/x/everything/best"

    timeperiods = []
    if sort =='top' and category is not None:
        timeperiods = top_timeperiod_urls(category.name)
        active_period_url = top_url(category.name, kwargs.get('year'), kwargs.get('month'), kwargs.get('day'))

    sort_types = []
    if category is not None:
        if sort in ["active", "new"]:
            sort_types.extend([
                ('active threads', '/x/%s/active' % category.name),
                ('new posts', '/x/%s/new' % category.name)
            ])
            active_sort_url = '/x/%s/%s' % (category.name, sort)

    nav_data = nav.dump_json()

    front_data.update(locals())

    if request.is_mobile:
        return r2r_jinja("mobile/browse.html", front_data)

    return r2r_jinja("comment/explore.html", front_data)

def flagged(request):
    moderations = []

    def moderate(comment, mod_type, allow_rejudge=False):
        if not allow_rejudge and comment.judged:
            moderations.append(u'%s was already judged as %s (you picked %s)'
                               % (comment.id, comment.get_visibility_short_name(), mod_type))
            return

        if mod_type == 'blocked' and comment.reply_content:
            comment.reply_content.moderate_and_propagate(Visibility.DISABLED, request.user)
            moderations.append('%s => blocked' % comment.reply_content_id)
        else:
            comment.moderate_and_save(getattr(Visibility, mod_type.upper()), request.user)
            moderations.append('%s => %s' % (comment.id, mod_type))

        # Handle sending a warning to a user. Do it only after verifying the comment hasn't already been judged
        # (and user already warned).
        if request.POST.get('comment_%s_warn_user' % comment.id):
            warning_id = {"public": 0, "hidden": 1, "disabled": 2, "blocked": 2}[mod_type]
            if warning_id:
                UserWarning.send_stock_comment_warning(comment, warning_id, request.user)

        # Handle the checkbox for also applying the moderation choice to replies.
        if request.POST.get('comment_{0}_also_replies'.format(comment.id)):
            for reply in comment.replies.all():
                reply_mod = mod_type
                if reply_mod == 'blocked' and not reply.reply_content:
                    reply_mod = 'disabled'
                moderate(reply, reply_mod, allow_rejudge=True)

    # Handle form submission if there are any POST keys.
    for name in request.POST.keys():
        match = re.match('comment_(\d+)_moderate', name)
        if match:
            (cid,) = match.groups()
            comment = Comment.all_objects.get(id=int(cid))
            mod_type = request.POST[name]
            moderate(comment, mod_type)

    if settings.PROJECT == 'canvas':
        mod_actions = ['public', 'curated', 'hidden', 'disabled', 'blocked']
    elif settings.PROJECT == 'drawquest':
        mod_actions = ['public', 'disabled']

    return render_to_response('flagged.django.html', {
        'mod_actions': mod_actions,
        'moderations': moderations,
        'comments': flagged_comments(),
    }, context_instance=RequestContext(request))

def staff_exception(request):
    """ Used for testing sentry. """
    raise Exception('did it work??')

@require_staff
def staff_noop(request):
    """
    Used to test the ResponseGuard middleware, which should raise an exception for not returning an
    HTTP response here.
    """
    return {}

@redirect_trailing
@require_user
def user_edit(request, username):
    viewer_is_staff = request.user.is_authenticated() and request.user.is_staff

    if request.user.username != username and not viewer_is_staff:
        raise PermissionDenied()

    user = get_object_or_404(User, username=username)
    current = user.userinfo.profile_image
    show_start_options = current is None
    bio_text = ""

    try:
        start_content = Content.all_objects.get(id=Content.DRAW_FROM_SCRATCH_PK).details()
    except Content.DoesNotExist:
        start_content = None

    if current is not None:
        start_content = current.reply_content.details()
        bio_text = current.reply_text
    else:
        bio_text = user.userinfo.bio_text

    thread_op = current
    if current is not None and current.parent_comment:
        thread_op = current.parent_comment

    ctx = {
        'start_content': start_content,
        'show_start_options': current is None,
        'viewer_is_staff': viewer_is_staff,
        'current_comment': current.details() if current is not None else None,
        'bio_text': bio_text,
        'thread_op': thread_op.details() if thread_op is not None else None,
    }
    return r2r_jinja("user/profile_edit.html", ctx, request)

@redirect_trailing
def user_view(request, username, userpage_type):
    nav = browse.Navigation.load_json_or_404({
        'userpage_type': userpage_type,
        'user': username,
        'offset': request.GET.get('offset'),
        'mobile': request.is_mobile,
    })

    nav_data = nav.dump_json()

    posts = browse.get_user_data(request.user, nav)

    viewer_is_staff = request.user.is_authenticated() and request.user.is_staff
    user = get_object_or_404(User, username=username)
    private_beta_member = (user.id <= 63015)
    user_is_staff = user.is_staff
    friendlyname = "you" if user == request.user else username
    # A template variable that tells us if the current user is viewing her profile.
    user_is_self = user == request.user
    user_can_see_anonymous = (request.user == user or viewer_is_staff)
    showing_anonymous = True

    viewer_is_following = request.user.is_authenticated() and request.user.is_following(user)

    hide_userpage_from_google = user.has_lab('hide_userpage_from_google')

    if userpage_type == 'top' or userpage_type == 'top_anonymous':
        sort_method = 'top'
    elif userpage_type == 'new' or userpage_type == 'new_anonymous':
        sort_method = 'new'
    elif userpage_type == 'stickered':
        sort_method = 'stickered'

    # Can this comment be deleted by this user?
    # We only want to show the delete button if the user is looking at her user page. So we suppress it in the
    # browse pages for two reasons:
    # 1. It adds clutter to the page. There is already a lot of stuff going on in browse pages.
    # 2. It might encourage deletes.
    show_delete_option = user_is_self and userpage_type not in ['stickered']

    sort = sort_method
    # The Jinja template expects "posts" to be called "tiles".
    tiles = posts
    render_options = tile_render_options(sort, False)

    avatar_comment = None
    bio = ""

    if user.userinfo.profile_image is not None:
        avatar_comment = Comment.details_by_id(user.userinfo.profile_image.id)()
        bio = user.userinfo.profile_image.reply_text

    if request.is_mobile:
        return r2r_jinja('mobile/user.html', locals())

    return r2r_jinja('user/profile.html', locals())

def about(request):
    peeps = []
    comments = []
    for short_id in settings.ABOUT_PAGE_COMMENTS:
        mapping_id = get_mapping_id_from_short_id(short_id)
        comment = get_object_or_404(Comment.all_objects, id=mapping_id)
        comments.append(comment)
        peeps.append(TileDetails(comment.details()))

    tiles = TileDetails.from_queryset_with_viewer_stickers(request.user, comments)
    sort = None
    show_pins = False
    render_options = tile_render_options(sort, show_pins)

    return r2r_jinja("about.html", locals())

@require_unblocked_ip
@require_secure
def canvas_login(*args, **kwargs):
    return login(*args, **kwargs)

@require_unblocked_ip
def drawquest_login(*args, **kwargs):
    return login(*args, **kwargs)

def login(request, default_next='/', staff_protocol='https'):
    def is_secure_password(pw):
        has = lambda cs: any(char in cs for char in pw)
        return len(pw) >= 8 and has(string.lowercase) and has(string.uppercase) and has(string.digits)

    def valid_slug(raw):
        raw = raw.lstrip('#').strip()
        allowed = string.letters + string.digits + '_'
        def process(c):
            if c in allowed:
                return c
            elif c in string.whitespace:
                return '_'
            else:
                return ''

        return (''.join(map(process, raw)))[:20]

    cookies_to_delete = []
    next_ = get_next(request)

    if request.method == 'GET':
        return r2r_jinja('user/login.html', locals(), request)

    signed_request = request.POST.get(u'signed_request', None)
    facebook_id = request.POST.get(u'facebook_id', None)

    if signed_request and facebook_id:
        user = authenticate(request, facebook_id, signed_request)
        if user is None:
            return r2r_jinja('user/login.html', locals(), request)
        # this is a total hack because we don't care to write a backend for the above authenticate method
        user.backend = settings.AUTHENTICATION_BACKENDS[0]
    else:
        username = valid_slug(request.POST.get('username', ''))
        password = request.POST.get('password')

        if check_rate_limit(request, username):
            message = "Too many retries. Wait a minute and try again."
            return r2r_jinja('user/login.html', locals(), request)

        user = auth.authenticate(username=username, password=password)
        if user is None:
            if User.objects.filter(username=username).exists():
                message = "Incorrect username or password."
            else:
                message = "Incorrect username or password."
            return r2r_jinja('user/login.html', locals(), request)

        if user.is_staff:
            if is_secure_password(password):
                next_ = make_absolute_url(next_ or default_next, protocol=staff_protocol)
            else:
                message = ("User is staff and has an insecure password. Please create a more secure one (8 or more "
                           "characters, mixed case and has numbers). Use password reset to fix this.")
                return r2r_jinja('user/login.html', locals(), request)

    auth.login(request, user)

    try:
        (key, post_data) = after_signup.get_posted_comment(request)
        if post_data:
            next_ = post_comment(request, user, post_data, persist_url=False).details().url
            cookies_to_delete.append(after_signup.make_cookie_key('post_comment'))
    except KeyError:
        pass

    def cleanup(response):
        for k in cookies_to_delete:
            response.delete_cookie(k)
        return response

    if next_:
        next_params = request.GET.copy()
        if 'next' in next_params:
            del next_params['next']
        next_params = '?' + urllib.urlencode(next_params) if next_params else ''
        return cleanup(HttpResponseRedirect(next_ + next_params))
    else:
        return cleanup(HttpResponseRedirect('/'))

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/')

def join(request):
    return HttpResponseRedirect('/signup')

def signup_share_prompt(request):
    post_pending_signup_url = request.user.kv.post_pending_signup_url.get()
    return r2r('share_prompt.django.html', locals())

def calculate_vintage(start):
    days = range(0, 12)
    vintages = []
    for d in days:
        date = start - datetime.timedelta(d*30)
        vintages.append(User.objects.filter(date_joined__lte=date).order_by('-id')[0].id)

    uniques = [int(n) for n in Metrics.view.uniques_breakdown(start)]

    # First vintage is all new registrants, last vintage is > 14 days with no upper bound
    vintages = [100**10] + vintages + [0]

    data = ([len([id for id in uniques if v_before <= id < v_after])
             for (v_before, v_after) in zip(vintages[1:], vintages[:-1])])
    return [{'name': 'uniques', 'data': data}]

def calculate_cohort(start, length, cohorts, rollup=1):
    vintages = ([User.objects.filter(date_joined__lte=start - datetime.timedelta(d)).order_by('-id')[0].id
                 for d in range(-1, cohorts*rollup, rollup)])
    cohort_ranges = zip(vintages[1:], vintages[:-1])
    pull_length = max(length, cohorts)
    unique_days = ([set(Metrics.view.uniques_breakdown(start - datetime.timedelta(d)))
                    for d in range(pull_length*rollup)])
    uniques = ([reduce(operator.__or__,
                       [unique_days[run*rollup+d] for d in range(rollup)], set()) for run in range(pull_length)])
    return [
        {
            'name': str(n),
            'data': [
                round(len([id for id in uniques[n-m] if L <= id < U]) * 100.0 / (U-L), 2)
                for m in range(length)
                if n-m >= 0 and U-L != 0
            ],
        }
        for n, (L, U) in enumerate(cohort_ranges)
    ]

def staff_vintage(request):
    vintage_today = calculate_vintage(datetime.date.today())
    vintage_yesterday = calculate_vintage(datetime.date.today() - datetime.timedelta(1))
    daily_cohorts = calculate_cohort(datetime.date.today(), 7, 7)
    weekly_cohorts = calculate_cohort(datetime.date.today(), 8, 8, rollup=7)
    return r2r('staff/vintage.django.html', locals())

def staff_vanity_metrics(request):
    ytd = bool(request.GET.get('ytd'))
    enum_days = days if not ytd else days_ytd
    posts = Comment.all_objects.count()
    # Use the last id instead of count() so we can use this more reliably for email sending ranges.
    users = User.objects.order_by('-id')[0].id
    stickers = CommentSticker.objects.count()

    graphs = []
    for cat_name, arg_lists in Metrics.names:
        counts, uniques, unique_ips = [], [], []
        hourly_counts, hourly_uniques, hourly_unique_ips = [], [], []
        for args in arg_lists:
            name = args[0]
            metric = getattr(Metrics, name)
            counts.append({
                'name': name,
                'data': [metric.daily_count(d) for d in enum_days()],
            })
            uniques.append({
                'name': name,
                'data': [metric.daily_uniques(d) for d in enum_days()],
            })
            unique_ips.append({
                'name': name,
                'data': [metric.daily_uniques(d, True) for d in enum_days()],
            })

            if not ytd:
                hourly_counts.append({
                    'name': name,
                    'data': [metric.hourly_count(h) for h in hours()],
                })
                hourly_uniques.append({
                    'name': name,
                    'data': [metric.hourly_uniques(h) for h in hours()],
                })
                hourly_unique_ips.append({
                    'name': name,
                    'data': [metric.hourly_uniques(d, True) for d in hours()],
                })

        graphs.append({'name': cat_name + ' counts', 'data': counts, 'primary': True, 'primary_name': cat_name})
        graphs.append({'name': cat_name + ' uniques', 'data': uniques, 'primary': False})
        graphs.append({'name': cat_name + ' unique ips', 'data': unique_ips, 'primary': False})
        if not ytd:
            graphs.append({'name': cat_name + ' hourly counts', 'data': hourly_counts, 'primary': False})
            graphs.append({'name': cat_name + ' hourly uniques', 'data': hourly_uniques, 'primary': False})
            graphs.append({'name': cat_name + ' hourly unique ips', 'data': hourly_unique_ips, 'primary': False})

    return r2r('staff/vanity_metrics.django.html', locals())

def time_compare_graph(title, data, days):
    return {
        'chart': {
            'defaultSeriesType': 'line',
            'zoomType': 'x,'
        },
        'title': {
            'text': title,
            'x': -20,
        },
        'xAxis': [
            {
                'type': 'datetime',
                'maxZoom': 48 * 3600 * 1000,
                'tickInterval': days * 24 * 3600 * 1000,
            },
            {
                'type': 'datetime',
                'maxZoom': 48 * 3600 * 1000,
                'tickInterval': days * 24 * 3600 * 1000,
                'offset': 20,
            },
        ],
        'yAxis': {
            'title': {
                'text': 'Count',
            },
            'min': 0,
        },
        'series': data,
    }

def trailing_days(*args):
    for i in reversed(range(*args)):
        yield datetime.datetime.today() - datetime.timedelta(i)

class Grapher(object):
    def __init__(self, request):
        view = request.GET.get('view', 'weekly')

        if view == 'monthly':
            self.timespan = 28
            self.tick = 7
        else:
            self.timespan = 7
            self.tick = 1

    def gen_trailing(self, name, fun):
        def gen_point(d):
            return {
                'y': fun(d),
                'x': jstime_from_dt(d),
            }

        data = [
            {
                'name': 'Last Week',
                'data': [gen_point(d) for d in trailing_days(self.timespan, self.timespan*2)],
                'xAxis': 1,
                'color': "#99B"
            },
            {
                'name': 'This Week',
                'data': [gen_point(d) for d in trailing_days(0, self.timespan)],
                'xAxis': 0,
                'color': '#00B',
            }
        ]
        return time_compare_graph(name, data, self.tick)

def staff_pulse(request):
    g = Grapher(request)
    M = lambda metric, fun_name='daily_uniques': lambda d: getattr(metric, fun_name)(d)

    graphs = [
        g.gen_trailing('Daily Signups', M(Metrics.signup, 'daily_count')),
        g.gen_trailing('DAU (Daily Unique Viewers)', M(Metrics.view)),
        g.gen_trailing('Daily Unique Stickerers', M(Metrics.sticker)),
        g.gen_trailing('Daily Unique Posters', M(Metrics.post)),
    ]

    return r2r('staff/graphs.django.html', locals())

def staff_action(request):
    stickerers, posters, viewers = [], [], []

    def safediv(num, div):
        return float(num) / div if div != 0 else 0

    def intersect(metric, today):
        yesterday = today - datetime.timedelta(1)
        yesterday_signups = Metrics.signup.uniques(yesterday)
        today_metric = metric.uniques(today)
        returning_metric = RedisSet(gen_temp_key())
        redis.sinterstore(returning_metric.key, [yesterday_signups.key, today_metric.key])
        return safediv(returning_metric.scard(), yesterday_signups.scard())

    g = Grapher(request)
    M = lambda metric: lambda d: intersect(metric, d) * 100

    graphs = [
        g.gen_trailing('2nd day viewer %', M(Metrics.view)),
        g.gen_trailing('2nd day stickerers %', M(Metrics.sticker)),
        g.gen_trailing('2nd day posters %', M(Metrics.post)),
    ]

    return r2r('staff/graphs.django.html', locals())

def numbers(request):
    now = time.time()
    trailing_7day = now - 7 * 24 * 60 * 60

    fmt = lambda n, tot: "%0.0f (%0.2f%%)" % (n, float(n)/tot*100) if tot else None

    all_users = User.objects.all()
    all_images = Content.all_objects.count()
    all_remixes = Content.all_objects.exclude(remix_of=None).count()

    l7d_images = Content.all_objects.filter(timestamp__gt=trailing_7day).count()
    l7d_remixes = Content.all_objects.exclude(remix_of=None).filter(timestamp__gt=trailing_7day).count()

    max_user_id = User.objects.order_by('-id')[0].id
    trailing_1000_users = User.objects.filter(id__gte=max_user_id-1000)

    women = lambda u: u.filter(facebookuser__gender=Gender.FEMALE).count()
    viral = lambda u: (u.aggregate(c=Count('sent_invites__invitee')).get('c', 0)
                       + u.aggregate(c=Count('facebook_sent_invites__invitee')).get('c', 0))

    sections = [
        (   'All time',
            [('Images', all_images), ('Remixes', fmt(all_remixes, all_images))]
        ),
        (   'Last 7 days',
            [('Images', l7d_images), ('Remixes', fmt(l7d_remixes, l7d_images))]
        ),
        (   'Trailing 1000 users',
            [('Women', women(trailing_1000_users)), ('Invited users (virality)', viral(trailing_1000_users))]
        ),
        (   'All Users',
            [('Women', women(all_users)), ('Invited users (virality)', viral(all_users))]
        ),
    ]

    trailing_7day_dau = [Metrics.view.daily_uniques(d) for d in days(7)]
    users = User.objects.count()
    daily = sum(trailing_7day_dau) / 7.0
    weekly = redis.scard(Metrics.view.trailing_uniques(7, gen_temp_key()))
    monthly = redis.scard(Metrics.view.trailing_uniques(30, gen_temp_key()))

    sections += [
        (   'Uniques (by view)',
            [
                ('all users', users),
                ('daily (trailing 7day average)', fmt(daily, users)),
                ('weekly (trailing 7day cumulative)', fmt(weekly, users)),
                ('monthly (trailing 30day cumulative)', fmt(monthly, users)),
            ],
        ),
    ]

    #u = lambda table, cutoff: fmt(User.objects.annotate(count=Count(table)).filter(count__gt=cutoff).count(), users)
    #
    #sections += [
    #    (   'Uniques (actions)',
    #        [
    #            ('all users', users),
    #            ('stickered', u('commentsticker', 0)),
    #            ('stickered 25 times', u('commentsticker', 24)),
    #            ('posted', u('comment', 0)),
    #            ('posted 25 times', u('comment', 24)),
    #            ('remixed', u('comment__reply_content__remix_of', 0)),
    #            ('remixed 25 times', u('comment__reply_content__remix_of', 24)),
    #        ],
    #    ),
    #]

    return r2r('staff/numbers.django.html', locals())

def unsubscribe(request):
    token = request.REQUEST.get('token', '')
    email = request.REQUEST.get('email')
    user_id = request.REQUEST.get('user_id')

    token_user = User.objects.get_or_none(id=user_id) if user_id else None

    unsubscribed = False
    unsubscribed_on_get = False

    if user_id and util.token(user_id) == token and token_user:
        user = token_user

    elif email and util.token(email) == token:
        # No user_id associated with the sent email, unsubscribe this email address from all email
        find_user = User.objects.filter(email=email)
        # If there is one and only one user with that email address, then pick them, otherwise we'll fall back to just an email address
        user = find_user[0] if find_user.count() == 1 else None

    elif request.user.is_authenticated():
        # Token mismatch, but we have a logged in user.
        user = request.user

    else:
        error = True
        return r2r('unsubscribe.django.html', locals())

    all_actions = EmailChannel.all_handled_actions()

    if user:
        subscriptions = user.kv.subscriptions

        # We need to handle any posts that are passed in the URL
        comment_id = request.GET.get('post')
        if comment_id:
            try:
                unsubscribed_post = Comment.objects.get(pk=int(comment_id))
            except ObjectDoesNotExist:
                pass
            else:
                user.redis.mute_thread(unsubscribed_post)
                unsubscribed_from_thread = unsubscribed_on_get = unsubscribed = True
                Metrics.mute_thread.record(request)

        # Support for unsubscribe headers.
        # We support passing in 'actions'
        action = request.REQUEST.get('action')
        if action and action in EmailChannel.all_handled_actions():
            unsubscribed_on_get = unsubscribed = True
            user.kv.subscriptions.unsubscribe(action)
            Metrics.unsubscribe_action.record(request, action=action, method=request.method)

        if request.method == 'POST':
            # Handle the 'ALL' case separately because the semantics for it are inverted.
            # ie, if ALL is checked, it means to DISABLE. While if REMIXED is checked, it means ENABLE.
            handle_unsubscribe_post(user, request.REQUEST, request)

        # We use this dictionary to render the checkboxes in the html.
        unsubscribed = unsubscribed or get_unsubscriptions(user, all_actions)

        unsubscribed_settings = get_unsubscriptions(user)
    else:
        unsubscribe_newsletter(email)
        unsubscribed = True
        Metrics.unsubscribe_email_address.record(request)

    return r2r('unsubscribe.django.html', locals())

#TODO this isn't a view, move it elsewhere
def handle_unsubscribe_post(user, actions_dict, request):
    subscriptions = user.kv.subscriptions
    all_actions = EmailChannel.all_handled_actions()

    unsubscribe_from_all = actions_dict.get('ALL', False)
    if unsubscribe_from_all:
        subscriptions.unsubscribe_from_all()
        Metrics.unsubscribe_all.record(request)
        return
    elif not subscriptions.can_receive('ALL'):
        # Remove the blanket ban, and honor individual preferences.
        subscriptions.subscribe('ALL')
        return

    # Handle the rest of the actions.
    for action in all_actions:
        if bool(actions_dict.get(action, False)):
            subscriptions.subscribe(action)
        else:
            # It was unchecked. So unsubscribe.
            subscriptions.unsubscribe(action)
            Metrics.unsubscribe_action.record(request, action=action, method=request.method)

def processlist(request):
    from django.db import connection
    cursor = connection.cursor()
    cursor.execute("SHOW FULL PROCESSLIST")
    processlist = cursor.fetchall()
    return r2r('staff/processlist.django.html', locals())

@require_user
def group_new(request):
    ctx = {
        'found_limit_reached': request.user.found_limit_reached(),
        'request': request,
    }
    return r2r('group/new.django.html', ctx)

def group_about(request, name):
    category = get_object_or_404(Category, name=name)
    category_disabled = category.visibility == Visibility.DISABLED
    founder = category.founder
    moderators = list(category.moderators.values_list('username', flat=True))
    can_modify_group = category.can_modify(request.user)
    can_disable_group = category.can_disable(request.user)
    has_form = can_modify_group or can_disable_group
    return r2r('group/about.django.html', locals())

@require_user
def draw(request):
    # Get the content_id of what we are remixing, or our blank white PNG if nothing.
    cid = request.GET.get('cid', Content.DRAW_FROM_SCRATCH_PK)
    remixing = get_object_or_404(Content.all_objects, id=cid).details()
    return r2r('draw.django.html', locals())

def staff_user_view(request, username, key="user"):
    user = get_object_or_404(User, username=username)

    kwargs = {key: user}
    related = ['user', 'moderator']
    comment_log = CommentModerationLog.objects.filter(**kwargs).order_by('-id').select_related(*(related+['comment', 'comment__parent_comment']))[:100]
    user_log = UserModerationLog.objects.filter(**kwargs).select_related(*related)

    time_dilation = user.kv.time_dilation.get()
    time_dilation_start = user.kv.time_dilation_start.get()
    time_dilation_end = user.kv.time_dilation_end.get()
    if time_dilation_start and time_dilation_end:
        time_dilation_days = int((time_dilation_end - time_dilation_start) / 86400)
    else:
        time_dilation_days = 0

    sorted_logs = sorted(list(comment_log) + list(user_log), key=lambda log: -log.timestamp)

    # Warm the in-process-cache for the template uses of reply_content.details.
    CachedCall.multicall([log.comment.reply_content.details for log in comment_log if log.comment.reply_content])

    logs = [(log, render_to_string('staff/modlog/' + log.log_template, {'log': log})) for log in sorted_logs]

    return r2r('staff/user_view.django.html', locals())

def staff_user_ip_history(request, username):
    user = get_object_or_404(User, username=username)
    ip_history = [(int_to_ip(ip), timestamp) for (ip, timestamp) in user.redis.ip_history.with_scores[:]]
    return r2r('staff/ip_history.django.html', locals())

def staff_ip_user_history(request, ip):
    ip_int = ip_to_int(ip)
    history = IP(ip_int).user_history.with_scores[:]
    users = User.objects.in_bulk_list([user for (user, ts) in history])
    history = zip(users, [ts for (user, ts) in history])
    return r2r('staff/user_history.django.html', locals())

def staff_user_browse(request):
    if request.method == "POST":
        email = request.POST['email']
        matched_user = User.objects.get_or_none(email=email)
    recent_disablings = User.objects.filter(is_active=False, user_warnings__disable_user=True).annotate(issued=Max('user_warnings__issued')).order_by('-issued')
    return r2r('staff/user_browse.django.html', locals())

@require_user
def warning(request):
    if request.method == "POST":
        for name in request.POST.keys():
            match = re.match('confirm_(\d+)', name)
            if match:
                warning_id, = match.groups()
                warning = UserWarning.objects.get(user=request.user, id=warning_id)
                warning.confirm()

    warnings = list(UserWarning.objects.filter(user=request.user, confirmed=0))

    if warnings:
        return r2r('warning.django.html', locals())
    else:
        return HttpResponseRedirect('/warning/code_of_conduct')

def blocking_coc(request):
    if request.method == "POST":
        if UserWarning.objects.filter(user=request.user, confirmed=0):
            return HttpResponseRedirect('/warning')
        else:
            request.user.redis.user_kv.hdel('sandbox')
            return HttpResponseRedirect('/')
    else:
        return r2r_jinja('blocking_coc.html', locals(), request)

@require_POST
def staff_user_warn(request, username):
    user = User.objects.get(username=username)

    UserWarning.send_custom_warning(user, request.POST['message'], request.user)

    return HttpResponseRedirect('/staff/user/' + user.username)

@require_POST
def staff_user_ban(request, username):
    user = User.objects.get(username=username)

    user.is_active = False
    user.save()

    UserWarning.send_custom_warning(user, request.POST['message'], request.user, deactivate_user=True)

    return HttpResponseRedirect('/staff/user/' + user.username)

@require_POST
def staff_user_unban(request, username):
    user = User.objects.get(username=username)

    user.is_active = True
    user.save()

    UserModerationLog.append(
        user=user,
        moderator=request.user,
        action=UserModerationLog.Actions.reactivate_user,
    )

    return HttpResponseRedirect('/staff/user/' + user.username)

def staff_user_dilate(request, username):
    user = User.objects.get(username=username)

    dilation = float(request.POST['dilation'])
    dilation_days = int(request.POST['dilation_days'])

    if dilation_days == 0:
        try:
            user.kv.time_dilation_start.delete()
            user.kv.time_dilation_end.delete()
        except KeyError:
            pass
    else:
        user.kv.time_dilation_start.set(time.time())
        user.kv.time_dilation_end.set(time.time() + (dilation_days * 86400))

    user.kv.time_dilation.set(dilation)

    return HttpResponseRedirect('/staff/user/' + user.username)

@require_staff
def staff_api_console(request):
    """ Shows an html wrapper around our APIs that staff can use. """
    from canvas.js_api import get_api_calls

    api_dict = defaultdict(lambda: [])
    # Group apis by their prefix.
    api_key = lambda func: func.url.strip("/").split("/")[1]
    functions = get_api_calls()
    for key, api_calls in itertools.groupby(functions, api_key):
        api_dict[key].extend(api_calls)

    apis = []
    for key, api_calls in api_dict.items():
        apis.append(dict(name=key, commands=api_calls))
    # Order apis alphabetically
    apis = sorted(apis, key=lambda entry: entry.get("name"))
    # Inspect it.
    # @todo: Add a "staff" api for staff only calls.
    #apis = [dict(path="/api/", name="Canvas API", commands=functions)]
    return r2r("api_wrapper.django.html", dict(apis=apis, request=request))

@require_staff
def epic_sticker_messages(request):
    stickers = CommentSticker.objects.exclude(epic_message='').order_by('-id')
    total = len(stickers)
    return r2r('staff/epic_sticker_messages.django.html', locals())

@redirect_trailing
def remix_share_page(request):
    # Get the branch of the experiment they are in.
    share_urls = [
        '/d/njs1h',
        '/d/mms9r/reply/1056799',
        '/d/nnseg',
        '/d/ncmgj',
        '/d/m1y5q',
        '/d/n4g2r',
        '/d/lvyao',
        '/d/n752j',
        '/d/f93h8',
        '/d/na49a',
    ]
    redirect_url = choice(share_urls) + '?remix'
    if 'ga' in request.GET:
        redirect_url += '&ga'
    return HttpResponseRedirect(redirect_url)

def debug_fact_stream(request):
    return r2r('debug_fact_stream.django.html', {
        'request': request,
        'funnels': dict((name, [step.name for step in funnel.steps],)
                        for name,funnel in Funnels.by_name.iteritems()),
        'debug_fact_channel': fact.debug_fact_channel().sync(),
    })

def sticker_values(request):
    sorted_stickers = sorted([(stick.sort_key(1), stick) for stick in stickers.all_stickers()], reverse=True)
    return r2r('staff/sticker_values.django.html', locals())

def stamps_used(request, content):
    content = Content.objects.get(id=content)
    stamps = content.stamps_used.all()
    ctx = {
        'content': content,
        'stamps': stamps,
    }
    return r2r_jinja('stamps_used.html', ctx, request)

def csrf_token(request):
    return HttpResponse(csrf.get_token(request))


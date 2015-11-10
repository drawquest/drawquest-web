from django import template
from django.conf.urls import *
from django.views.decorators.cache import cache_page
from django.views.generic import RedirectView

from canvas.shortcuts import direct_to_template
from canvas.url_util import re_slug, re_int, re_group_slug, re_year, re_month, re_day, maybe
from canvas.view_guards import require_staff, require_user
from drawquest import api
from website import urls as canvas_urls
from drawquest.apps.quests.urls import top_comments_urls


def cached(view):
    return cache_page(60*20, key_prefix='website_v2')(view)


admin_urls = patterns('',
    (r'^$', RedirectView.as_view(url='/admin/x/everything')),
    (r'^', include(canvas_urls.root_urls)),
    (r'^staff', include('drawquest.apps.staff.urls')),
    (r'^staff/moderation', include('drawquest.apps.whitelisting.urls')),
    (r'^staff/colors', include('drawquest.apps.palettes.urls')),
    (r'^staff/vanity_metrics', 'drawquest.views.vanity_metrics'),
    (r'^staff/explore', include('drawquest.apps.explore.urls')),
    (r'^staff/', include(canvas_urls.staff_urls)),
    (r'^api_console$', 'drawquest.apps.api_console.views.staff_api_console'),
    (r'^api_endpoints$', 'drawquest.apps.api_console.views.staff_api_endpoints'),

    (r'^quests/schedule', 'drawquest.apps.quest_scheduler.views.schedule'),
    (r'^quests/', include('drawquest.apps.quests.urls')),

    (r'^x/', include(canvas_urls.tag_browse_urls)),
    (r'^t/', include(canvas_urls.tag_browse_urls)),

    url(r'^p/' + re_slug('short_id')
               + maybe('/'+re_int('page'))
               + maybe('/reply/'+re_int('gotoreply'))
               + maybe('/(?P<sort_by_top>top)')
               + '/?$', 'apps.threads.views.thread'),
)

urlpatterns = patterns('canvas.views',
    url(r'^js_testing$', 'direct_to_django_template', kwargs={'template': 'drawquest_js_testing.django.html'}),

    url(r'^login$', 'drawquest_login', kwargs={'default_next': '/admin/staff', 'staff_protocol': 'http'}),
    url(r'^logout$', 'logout'),
)

urlpatterns += patterns('',
    (r'^download$', RedirectView.as_view(url='https://itunes.apple.com/us/app/drawquest-free-daily-drawing/id576917425?ls=1&mt=8')),

    (r'^accounts/', include('allauth.urls')),
    (r'^admin/', include(admin_urls)),
    (r'^bounces/', include('drawquest.apps.bounces.urls')),
    (r'^quests/', include(top_comments_urls)),
    (r'^api/', include(api.urls)),
    url(r'deauthorize_facebook_user', 'drawquest.apps.drawquest_auth.views.deauthorize_facebook_user'),
    url(r'^p/' + re_slug('short_id'), 'drawquest.apps.quest_comments.views.share_page'),
    (r'^password_reset$', RedirectView.as_view(url='/password_reset/')),
    (r'^password_reset/', include('drawquest.apps.drawquest_auth.urls')),
    (r'^quests/submit_quest', include('drawquest.apps.submit_quest.urls')),
    url(r'^unsubscribe$', 'drawquest.views.unsubscribe'),
    url(r'^quest_of_the_day$', 'drawquest.apps.quests.views.quest_of_the_day'),
    url(r'^q/' + re_slug('short_id') + r'/(?P<slug>[-\w]+)$', 'drawquest.apps.quests.views.quest', name='quest'),
    url(r'^q/' + re_slug('short_id'), 'drawquest.apps.quests.views.quest'),
    (r'^s/', include('apps.share_tracking.urls')),

    url(r'^$', 'drawquest.views.homepage'),
    (r'^about$', RedirectView.as_view(url='/mission')),
    url(r'^mission$', cached(direct_to_template), kwargs={'template': 'drawquest/mission.html'}),
    url(r'^team$', cached(direct_to_template), kwargs={'template': 'drawquest/team.html'}),
    url(r'^privacy$', cached(direct_to_template), kwargs={'template': 'drawquest/privacy.html'}),
    url(r'^terms$', cached(direct_to_template), kwargs={'template': 'drawquest/terms.html'}),
    url(r'^jobs$', cached(direct_to_template), kwargs={'template': 'drawquest/jobs.html'}),
    url(r'^support$', 'drawquest.views.support'),

    url(r'^palettes$', direct_to_template, kwargs={'template': 'drawquest/palettes.html'}),

    url(r'^app/about$', cached(direct_to_template), kwargs={'template': 'drawquest/app/about.html'}),
    url(r'^app/privacy$', cached(direct_to_template), kwargs={'template': 'drawquest/app/privacy.html'}),
    url(r'^app/terms$', cached(direct_to_template), kwargs={'template': 'drawquest/app/terms.html'}),
    url(r'^app/upgrade$', cached(direct_to_template), kwargs={'template': 'drawquest/upgrade.html'}),

    url(r'^app/profile_preview$', 'drawquest.apps.profiles.views.profile_preview'),
    url(r'^' + re_slug('username') + '$', 'drawquest.apps.profiles.views.profile'),
)

handler404 = 'drawquest.views.jinja_404'


PROTECTED_URLS = [
    'js_testing', 'logout', 'download', 'admin', 'quests', 'api',
    'password_reset', 'quests', 'unsubscribe', 'quest_of_the_day',
    'about', 'privacy', 'terms', 'jobs', 'support', 'palettes', 'app',

    # Speculative:
    'facebook', 'twitter', 'signup', 'signin', 'help', 'info', 'explore',
    'quest_comments', 'ios', 'signout', 'tos', 'terms_of_service',
    'category', 'categories', 'users', 'groups', 'questers', 'subscribe', 'osx', 'photos',
    'picture', 'wwdc', 'sxsw', 'contest', 'contests', 'profile', 'profiles', 'leaders', 'top',
    'holidays', 'sort', 'moderators', 'messages', 'fanmail', 'fan_mail',

    # Ones in-use that we may want to emminent domain at some point:
    #'android', 'apple', 'best', 'drawings', 'draw', 'quest', 'apps','login', 'user',
]

template.add_to_builtins('django.templatetags.i18n')


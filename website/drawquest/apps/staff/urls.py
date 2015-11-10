from django.conf.urls import *

from canvas.shortcuts import direct_to_template
from canvas.url_util import re_slug, re_int, re_group_slug, re_year, re_month, re_day, maybe


urlpatterns = patterns('drawquest.apps.staff.views',
    url(r'^$', direct_to_template, kwargs={'template': 'staff/portal.html'}),
    url(r'^/staff_stars$', 'staff_stars'),
    url(r'^/top_starred$', 'top_starred'),
    url(r'^/deep_links$', 'deep_links'),
    url(r'^/max_strokes/(?P<stroke_count>[0-9])$' , 'max_strokes'),
    url(r'^/user/' + re_slug('username') + '/ip_history$', 'user_ip_history'),
    url(r'^/user/' + re_slug('username') + '/activity_stream$', 'user_activity_stream'),
    url(r'^/user/' + re_slug('username') + '/iap$', 'user_iap_receipts'),
    url(r'^/ip/' + re_slug('ip') + '/user_history$', 'ip_user_history'),
    url(r'^/user/' + r'(?P<username_or_email>[a-zA-Z0-9_.,-\@]+)$', 'user'),
)
urlpatterns += patterns('',
    url(r'^/top_quests$', 'drawquest.apps.quests.views.staff_top_quests'),
    url(r'^/new_ugq$', 'drawquest.apps.quests.views.staff_new_ugq'),
)


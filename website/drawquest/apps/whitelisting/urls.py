from django.conf.urls import *
from canvas.shortcuts import direct_to_template
from canvas.view_guards import require_staff


urlpatterns = patterns('drawquest.apps.whitelisting.views',
    url(r'^$', 'moderation'),
    url(r'^/divvy/(?P<id_range>[0-9]-[0-9])$', 'moderation'),

    url(r'^/flagged$', 'flag_queue'),
    url(r'^/flagged/paginated/(?P<after_id>\d+)$', 'flag_queue_paginated'),

    url(r'^/new$', 'new'),
    url(r'^/new/divvy/(?P<id_range>[0-9]-[0-9])$', 'new_divvy'),
    url(r'^/new/paginated/(?P<after_id>\d+)$', 'new_paginated'),

    url(r'^/ugq$', 'ugq_moderation'),
    url(r'^/ugq/new$', 'ugq_new'),

    url(r'^/all$', 'all'),
    url(r'^/all/paginated/(?P<after_id>\d+)$', 'all_paginated'),

    url(r'^/disabled$', 'disabled'),
    url(r'^/disabled/paginated/(?P<after_id>\d+)$', 'disabled_paginated'),

    url(r'^/distrusted$', 'distrusted'),
)


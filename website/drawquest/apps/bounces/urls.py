from django.conf.urls import *

urlpatterns = patterns('drawquest.apps.bounces.views',
    url(r'^handle_notification$', 'handle_notification'),
)


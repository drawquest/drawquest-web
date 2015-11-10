from django.conf.urls import *

urlpatterns = patterns('drawquest.apps.explore.views',
    url(r'^$', 'staff_explore'),
)


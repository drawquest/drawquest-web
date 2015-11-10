from django.conf.urls import *

from drawquest.apps.palettes.views import ColorPackList, ColorList

urlpatterns = patterns('drawquest.apps.palettes.views',
    url(r'^$', ColorList.as_view()),
    url(r'^/packs$', ColorPackList.as_view()),
)


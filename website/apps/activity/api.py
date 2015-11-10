from datetime import timedelta as td

from django.conf import settings
from django.http import HttpResponse

from apps.activity import jinja_tags
from apps.activity.models import legacy_get_activity_stream_items, activity_stream_items
from canvas import knobs
from canvas.api_decorators import api_decorator
from canvas.metrics import Metrics
from canvas.view_guards import require_user
from drawquest.api_cache import cached_api
from drawquest.apps.quests import signals


urlpatterns = []
api = api_decorator(urlpatterns)


def _request_gatekeeper(request, later_than=None, earlier_than=None):
    return later_than is None and earlier_than is None

@api('iphone_activities')
@require_user
@cached_api(
    timeout=td(days=14),
    key=['iphone_activities', 'v2'],
    request_gatekeeper=_request_gatekeeper,
    add_user_to_key=True,
)
def iphone_activities(request, later_than=None, earlier_than=None):
    """
    `later_than` is not paginated and instead returns an error code if there are too many
    items requested. Can't specify both `later_than` and `earlier_than`.
    """
    activities = activity_stream_items(request.user, later_than=later_than, earlier_than=earlier_than, iphone=True)
    return {'activities': activities}

@api('activities')
@require_user
@cached_api(
    timeout=td(days=14),
    key=['activities'],
    request_gatekeeper=_request_gatekeeper,
    add_user_to_key=True,
)
def ipad_activities(request, later_than=None, earlier_than=None):
    """
    `later_than` is not paginated and instead returns an error code if there are too many
    items requested. Can't specify both `later_than` and `earlier_than`.
    """
    activities = activity_stream_items(request.user, later_than=later_than, earlier_than=earlier_than)
    return {'activities': activities}


def invalidate_caches(user_id):
    for func in [ipad_activities, iphone_activities]:
        func.delete_cache(None, None, user=user_id)



# DEPRECATED.
@api('activity_stream')
@require_user
def activity_stream(request, earliest_timestamp_cutoff=None):
    if settings.PROJECT == 'drawquest':
        return HttpResponse('')

    activities = legacy_get_activity_stream_items(request.user, earliest_timestamp_cutoff=earliest_timestamp_cutoff)

    Metrics.activity_stream_infinite_scroll.record(request)

    return HttpResponse(u''.join([jinja_tags.activity_stream_item(activity, request.user)
                                  for activity in activities]))

@api('mark_activity_read')
@require_user
def mark_activity_read(request, activity_id):
    request.user.redis.activity_stream.mark_read(activity_id)

@api('mark_all_activities_read')
@require_user
def mark_all_activities_read(request):
    request.user.redis.activity_stream.mark_all_read()


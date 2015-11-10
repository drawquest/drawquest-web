from datetime import timedelta as td

from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404

import canvas.signals
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff
from drawquest import knobs
from drawquest.api_cache import cached_api
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quest_comments.api import quest_comments
from drawquest.apps.quests import models, signals, top
from drawquest.pagination import Paginator


urlpatterns = []
api = api_decorator(urlpatterns)


api('comments')(quest_comments)

@api('render_quest_preview')
@require_staff
def render_quest_preview(request, short_id):
    quest_preview = models.QuestPreview.get_by_short_id(short_id)

    ctx = {
        'quest_preview': quest_preview,
        'admin_view': True,
        'show_curation_info': False,
    }

    return HttpResponse(render_jinja_to_string('quests/quest_preview.html', ctx))

@api('archive')
@cached_api(
    timeout=td(days=1),
    namespace='quests',
    key=['quest_archive', 'v9'],
)
def quest_archive(request):
    return {'quests': models.archived_quests()}

@api('archive/v2')
@cached_api(
    timeout=td(days=1),
    namespace='quests',
    key=['quest_archive/v2', 'v3',
         lambda _, offset='top': offset],
)
def quest_archive_v2(request, offset='top'):
    quests, pagination = models.archived_quests(offset=offset)

    return {
        'quests': quests,
        'pagination': pagination,
    }

@api('inbox')
def quest_inbox(request):
    current_quest, quests = models.quest_inbox(request.user)

    ret = {'quests': quests}

    if current_quest is not None:
        ret['current_quest'] = current_quest

    return ret

@api('history')
def quest_history(request):
    return {'quests': models.quest_history(request.user)}

@api('top')
def top_quests(request):
    return {
        'quests': top.top_quest_details(),
        'current_quest': models.current_quest_details(),
    }

@api('current')
@cached_api(timeout=td(hours=2), namespace='quests', key=['current_quest', 'v3'])
def current_quest(request):
    return {'quest': models.current_quest_details()}

@api('quest')
def quest(request, quest_id):
    quest = get_object_or_404(models.Quest, id=quest_id)
    return {'quest': quest.details()}

@api('set_current_quest')
@require_staff
def set_current_quest(request, scheduled_quest_id):
    scheduled_quest = get_object_or_404(models.ScheduledQuest, id=scheduled_quest_id)
    scheduled_quest.set_as_current_quest()

@api('attribute_to_user')
@require_staff
def attribute_quest_to_user(request, scheduled_quest_id, username, attribution_copy):
    scheduled_quest = get_object_or_404(models.ScheduledQuest, id=scheduled_quest_id)
    user = get_object_or_404(User, username=username)
    scheduled_quest.quest.attribute_to_user(user, attribution_copy)

@api('clear_attribution')
@require_staff
def clear_quest_attribution(request, scheduled_quest_id):
    scheduled_quest = get_object_or_404(models.ScheduledQuest, id=scheduled_quest_id)
    scheduled_quest.quest.clear_attribution()

@api('onboarding')
@cached_api(timeout=td(days=1), key=[
    'onboarding_quest',
    'v3',
    knobs.ONBOARDING_QUEST_ID,
])
def onboarding_quest(request):
    return {'quest': models.Quest.objects.get(id=knobs.ONBOARDING_QUEST_ID).details()}

@api('dismiss_quest')
def dismiss_quest(request, quest_id):
    quest = get_object_or_404(models.Quest, id=quest_id)
    quest.dismiss(request.user)


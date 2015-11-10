from django.shortcuts import get_object_or_404

from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quests.models import Quest


urlpatterns = []
api = api_decorator(urlpatterns)

@api('invite_user_to_quest')
@require_user
def invite_user_to_quest(request, username, quest_id):
    invitee = get_object_or_404(User, username=username)
    quest = get_object_or_404(Quest, id=quest_id)

    quest.invited_users.invite(request.user, [invitee])


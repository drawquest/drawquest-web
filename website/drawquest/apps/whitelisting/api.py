from django.shortcuts import get_object_or_404

from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.models import UserModerationLog
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import Quest
from drawquest.apps.whitelisting import models

urlpatterns = []
api = api_decorator(urlpatterns)

@api('allow')
@require_staff
def whitelisting_allow(request, comment_id):
    try:
        comment = QuestComment.all_objects.get(id=comment_id)
    except QuestComment.DoesNotExist:
        comment = get_object_or_404(Quest.all_objects, id=comment_id)

    models.allow(comment, moderator=request.user)

@api('deny')
@require_staff
def whitelisting_deny(request, comment_id, disable_author=False):
    try:
        comment = QuestComment.all_objects.get(id=comment_id)
    except QuestComment.DoesNotExist:
        comment = get_object_or_404(Quest.all_objects, id=comment_id)

    models.deny(comment, moderator=request.user)

    if disable_author:
        author = comment.author
        author.is_active = False
        author.save()
        author.userinfo.details.force()

        UserModerationLog.append(
            user=author,
            moderator=request.user,
            action=UserModerationLog.Actions.deactivate_user,
        )

        for comment in author.comments.all():
            models.deny(comment)

@api('curate')
@require_staff
def whitelisting_curate(request, comment_id):
    try:
        comment = QuestComment.all_objects.get(id=comment_id)
    except QuestComment.DoesNotExist:
        comment = get_object_or_404(Quest.all_objects, id=comment_id)

    models.curate(comment, moderator=request.user)

@api('enable_auto_curate')
@require_staff
def whitelisting_enable_auto_curate(request):
    models.enable_auto_curate()

@api('disable_auto_curate')
@require_staff
def whitelisting_disable_auto_curate(request):
    models.disable_auto_curate()

@api('enable')
@require_staff
def whitelisting_enable(request, from_id=None):
    models.enable(from_id=from_id)

@api('disable')
@require_staff
def whitelisting_disable(request):
    models.disable()


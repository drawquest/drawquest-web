from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import slugify

from drawquest.apps.quests.models import ScheduledQuest, Quest
from drawquest.apps.quests import top
from drawquest.apps.gallery.models import top_gallery_comments
from canvas.redis_models import redis
from canvas.shortcuts import r2r_jinja
from canvas.util import base36decode_or_404, base36encode


def quest_of_the_day(request):
    quest = get_object_or_404(ScheduledQuest, id=redis.get('dq:current_scheduled_quest')).quest
    return redirect('quest', base36encode(quest.id), slugify(quest.title))

def quest(request, short_id, slug=None):
    quest = get_object_or_404(Quest, id=base36decode_or_404(short_id))

    _slug = slugify(quest.title)
    if _slug and _slug != slug:
        return redirect('quest', base36encode(quest.id), _slug)

    quest_details = quest.details()

    ctx = {
        'quest': quest_details,
        'comments': top_gallery_comments(quest, include_reactions=False),
        'quest_template_url': '',
        'original_quest_template_url': '',
    }

    if quest.reply_content_id:
        ctx.update({
            'quest_template_url': quest_details.content.get_absolute_url_for_image_type('gallery'),
            'original_quest_template_url': quest_details.content.get_absolute_url_for_image_type('original'),
        })

    return r2r_jinja('quests/quest.html', ctx, request)

def staff_top_quests(request):
    ctx = {
        'comments': top.top_quests(),
        'get_quest_score': top.get_quest_score,
    }
    return r2r_jinja('quests/staff_top_quests.html', ctx, request)

def staff_new_ugq(request):
    ctx = {
        'comments': Quest.objects.filter(ugq=True).order_by('-id')[:200],
        'get_quest_score': top.get_quest_score,
    }
    return r2r_jinja('quests/staff_top_quests.html', ctx, request)


import time

from canvas.redis_models import redis
from canvas.json import loads
from canvas.shortcuts import r2r_jinja
from canvas.models import UserInfo
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import Quest
from drawquest import knobs
from drawquest.apps.whitelisting.models import get_divvy_range, divvy, moderation_queue


def _moderation_context(sections, id_range=None):
    per_page = knobs.WHITELIST_COMMENTS_PER_PAGE

    if id_range is not None:
        from_, to = get_divvy_range(id_range)
        per_page = knobs.WHITELIST_COMMENTS_PER_PAGE * (to - from_)

    comments = []
    left_per_page = per_page
    for section in sections:
        if left_per_page == 0:
            break

        incoming_comments = section[:left_per_page]
        left_per_page -= len(incoming_comments)

        if id_range is None:
            comments.extend(list(incoming_comments))
        else:
            comments.extend(list(divvy(incoming_comments, from_, to)))

    if id_range is not None:
        comments = divvy(comments, from_, to)

    try:
        auto_curate = loads(redis.get('dq:auto_curate'))
    except TypeError:
        auto_curate = False

    min_ago = time.time() - 60

    return {
        'comments': comments,
        'auto_curate_enabled': auto_curate,
        'body_class': 'moderation',
    }

def moderation(request, id_range=None):
    flagged = QuestComment.unjudged_flagged().order_by('-id')
    unknown = QuestComment.by_unknown_users().order_by('-id').exclude(flags__undone=False)
    #distrusted = QuestComment.by_distrusted_users().order_by('-id').exclude(flags__undone=False)
    #trusted = QuestComment.by_trusted_users().order_by('-id').exclude(flags__undone=False)

    ctx = _moderation_context([flagged, unknown], id_range=id_range)

    ctx.update({
        'flagged_count': flagged.count(),
        'trusted_user_count': UserInfo.objects.filter(trusted=True).count(),
    })

    return r2r_jinja('whitelisting/moderation.html', ctx, request)

def ugq_moderation(request):
    flagged = Quest.unjudged_flagged().filter(ugq=True).order_by('-id')
    unknown = Quest.by_unknown_users().filter(ugq=True).order_by('-id').exclude(flags__undone=False)

    ctx = _moderation_context([flagged, unknown], id_range=None)

    ctx.update({
        'flagged_count': flagged.count(),
        'trusted_user_count': UserInfo.objects.filter(trusted=True).count(),
        'body_class': 'ugq_moderation',
    })

    return r2r_jinja('whitelisting/ugq_moderation.html', ctx, request)

def ugq_new(request):
    ctx = {
        'comments': Quest.unjudged().filter(ugq=True).order_by('-id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
        'body_class': 'new_ugq',
        'unjudged_count': Quest.objects.filter(ugq=True, judged=False).count(),
    }
    return r2r_jinja('whitelisting/new.html', ctx, request)

def distrusted(request, id_range=None):
    distrusted = QuestComment.by_distrusted_users().order_by('-id').exclude(flags__undone=False)
    
    ctx = _moderation_context([distrusted], id_range=id_range)
    return r2r_jinja('whitelisting/moderation.html', ctx, request)

def flag_queue(request):
    ctx = {
        'comments': QuestComment.unjudged_flagged().order_by('id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
        'body_class': 'flag_queue',
        'unjudged_count': QuestComment.objects.filter(judged=False).count(),
    }
    return r2r_jinja('whitelisting/flagged.html', ctx, request)

def flag_queue_paginated(request, after_id=None):
    ctx = {
        'comments': [],
    }
    return r2r_jinja('whitelisting/whitelist_items.html', ctx, request)

def new(request):
    ctx = {
        'comments': QuestComment.unjudged().order_by('-id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
        'body_class': 'new',
        'unjudged_count': QuestComment.objects.filter(judged=False).count(),
    }
    return r2r_jinja('whitelisting/new.html', ctx, request)

def new_divvy(request, id_range=None):
    from_, to = get_divvy_range(id_range)
    per_page = knobs.WHITELIST_COMMENTS_PER_PAGE * (to - from_)

    comments = divvy(QuestComment.unjudged().order_by('-id')[:per_page], from_, to)

    ctx = {
        'comments': comments,
        'body_class': 'new',
        'unjudged_count': QuestComment.objects.filter(judged=False).count(),
    }
    return r2r_jinja('whitelisting/new.html', ctx, request)

def new_paginated(request, after_id=None):
    ctx = {
        'comments': [],
    }
    return r2r_jinja('whitelisting/whitelist_items.html', ctx, request)

def all(request):
    ctx = {
        'comments': QuestComment.all_objects.all().order_by('-id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
        'body_class': 'all',
        'unjudged_count': QuestComment.objects.filter(judged=False).count(),
    }
    return r2r_jinja('whitelisting/all.html', ctx, request)

def all_paginated(request, after_id=None):
    ctx = {
        'comments': [],
    }
    return r2r_jinja('whitelisting/whitelist_items.html', ctx, request)

def disabled(request):
    ctx = {
        'comments': QuestComment.disabled().order_by('-id')[:knobs.WHITELIST_COMMENTS_PER_PAGE],
        'body_class': 'disabled',
        'unjudged_count': QuestComment.objects.filter(judged=False).count(),
    }
    return r2r_jinja('whitelisting/disabled.html', ctx, request)

def disabled_paginated(request, after_id=None):
    ctx = {
        'comments': [],
    }
    return r2r_jinja('whitelisting/whitelist_items.html', ctx, request)


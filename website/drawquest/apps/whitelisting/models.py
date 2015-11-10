from itertools import chain

from cachecow.cache import invalidate_namespace
from django.db import models

from canvas.json import backend_dumps
from canvas.models import Comment, CommentModerationLog, Visibility
from canvas.redis_models import redis
from drawquest import knobs
from drawquest.apps.quest_comments.models import QuestComment


def moderation_queue():
    sections = [
        QuestComment.unjudged_flagged().order_by('-id'),
        QuestComment.by_unknown_users().order_by('-id').exclude(flags__undone=False),
        QuestComment.by_distrusted_users().order_by('-id').exclude(flags__undone=False),
    ]

    return chain(*sections)

def get_divvy_range(id_range):
    try:
        from_, to = map(int, id_range.split('-'))
    except ValueError:
        raise Http404

    if from_ >= to:
        raise Http404

    return from_, to

def divvy(comments, from_, to):
    return [cmt for cmt in comments if int(str(cmt.id)[-1]) in range(from_, to + 1)]

def moderate(comment, visibility, moderator=None):
    if moderator:
        comment.judged = True

    comment.visibility = visibility
    comment.save()

    if moderator:
        CommentModerationLog.append(
            user=comment.author,
            comment=comment,
            moderator=moderator,
            visibility=visibility,
        )

    comment.visibility_changed()

def _prev_judged(author):
    prev_judged = Comment.all_objects.filter(judged=True, author=author)
    prev_judged = prev_judged.exclude(visibility=Visibility.UNPUBLISHED)

    if author.userinfo.trust_changed is not None:
        prev_judged = prev_judged.exclude(timestamp__lt=author.userinfo.trust_changed)

    return prev_judged

def allow(comment, moderator=None):
    if not comment.author.userinfo.trusted:
        if any(cmt.visibility == Visibility.PUBLIC for cmt in _prev_judged(comment.author)):
            comment.author.userinfo.trust()

    if comment.ugq:
        for reply in comment.replies.all():
            if reply.judged:
                continue

            moderate(reply, Visibility.PUBLIC)

    return moderate(comment, Visibility.PUBLIC, moderator=moderator)

def deny(comment, moderator=None):
    if comment.author.userinfo.trusted:
        if any(cmt.visibility == Visibility.DISABLED for cmt in _prev_judged(comment.author)):
            comment.author.userinfo.distrust()
    elif comment.author.userinfo.trusted is None:
        comment.author.userinfo.distrust()

    if comment.ugq:
        for reply in comment.replies.all():
            if reply.judged:
                continue

            moderate(reply, Visibility.DISABLED)

    return moderate(comment, Visibility.DISABLED, moderator=moderator)

def curate(comment, moderator=None):
    if comment.author.userinfo.trusted:
        curate_threshold = 8
    elif comment.author.userinfo.trusted is None:
        curate_threshold = 5
    else:
        curate_threshold = None

    if (curate_threshold
            and len(filter(lambda cmt: cmt.visibility == Visibility.CURATED,
                           _prev_judged(comment.author)))
                >= curate_threshold - 1):
        comment.author.userinfo.distrust()

    if comment.ugq:
        for reply in comment.replies.all():
            if reply.judged:
                continue

            moderate(reply, Visibility.CURATED)

    return moderate(comment, Visibility.CURATED, moderator=moderator)

def auto_moderate_unjudged_comments(user):
    """ Makes all unjudged comments by `user` either public or curated, depending on their trustedness. """
    if user.userinfo.trusted:
        visibility = Visibility.PUBLIC
    elif user.userinfo.trusted == False:
        visibility = Visibility.CURATED
    else:
        c = 0
        for comment in Comment.objects.filter(author=user, judged=False, visibility=Visibility.CURATED).order_by('id'):
            c += 1
            if c == 1:
                continue # Skip first curated drawing, which is intentional.
            moderate(comment, Visibility.PUBLIC)
        return

    comments = Comment.objects.filter(author=user, judged=False)
    comments = comments.exclude(visibility=visibility)

    comments.update(visibility=visibility)

    for comment in comments:
        comment.visibility_changed(force_cache=False)

def enable_auto_curate():
    redis.set('dq:auto_curate', backend_dumps(True))

def disable_auto_curate():
    redis.delete('dq:auto_curate')


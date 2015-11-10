from django.shortcuts import get_object_or_404, Http404

from canvas.models import get_mapping_id_from_short_id
from canvas.shortcuts import r2r_jinja
from drawquest.apps.playback.models import get_playback_data
from drawquest.apps.quest_comments.models import QuestComment


def playback(request, short_id):
    try:
        comment_id = get_mapping_id_from_short_id(short_id)
    except ValueError:
        raise Http404

    comment = get_object_or_404(QuestComment, id=comment_id)
    comment_details = comment.details()

    quest_details = comment.quest.details()

    playback_data = get_playback_data(comment)

    ctx = {
        'comment': comment_details,
        'quest': quest_details,
        'playback_data': playback_data,
    }

    return r2r_jinja('playback/playback.html', ctx, request)


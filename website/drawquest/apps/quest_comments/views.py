from django.shortcuts import get_object_or_404, Http404
from django.views.decorators.cache import cache_page

from canvas.models import get_mapping_id_from_short_id, UserKV
from canvas.shortcuts import r2r_jinja
from canvas.view_guards import require_staff
from drawquest.apps.drawquest_auth.details_models import UserDetails
from drawquest.apps.playback.models import get_playback_data
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.details_models import QuestDetails


@cache_page(5*60, key_prefix='website_v4')
def share_page(request, short_id):
    try:
        comment_id = get_mapping_id_from_short_id(short_id)
    except ValueError:
        raise Http404

    comment = get_object_or_404(QuestComment, id=comment_id)
    comment_details = comment.details()

    quest_details = QuestDetails.from_id(comment_details.quest_id)

    author_details = UserDetails.from_id(comment.author_id)

    ctx = {
        'quest': quest_details,
        'quest_template_url': '',
        'comment': comment_details,
        'author': author_details,
        'private_profile': bool(UserKV(comment.author_id).web_profile_privacy.get()),
    }

    if quest_details.content:
        ctx.update({
            'quest_template_url': quest_details.content.get_absolute_url_for_image_type('gallery'),
            'original_quest_template_url': quest_details.content.get_absolute_url_for_image_type('original'),
        })

    return r2r_jinja('quest_comments/share_comment_page.html', ctx, request)


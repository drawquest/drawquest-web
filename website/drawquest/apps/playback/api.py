from plistlib import readPlist, writePlistToString
import StringIO

from boto.exception import S3ResponseError
from django.conf.urls import url, patterns
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from canvas import json
from canvas.api_decorators import json_response
from canvas.exceptions import ServiceError
from canvas.storage import get_fs
from canvas.view_guards import require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.playback.models import Playback, save_playback_data, get_playback_data
from drawquest.apps.quest_comments.models import QuestComment, add_viewer_has_starred_field


urlpatterns = []
api = api_decorator(urlpatterns)


@api('playback')
def playback_drawing(request, comment_id):
    comment = get_object_or_404(QuestComment, id=comment_id)

    if request.user.is_authenticated():
        Playback.append(comment=comment, viewer=request.user)

    comment_details = comment.details()
    add_viewer_has_starred_field([comment_details], viewer=request.user)

    return {'comment': comment_details}

@api('playback_data')
def playback_data(request, comment_id):
    comment = get_object_or_404(QuestComment, id=comment_id)
    data = get_playback_data(comment)
    return {'playback_data': data}

@csrf_exempt
@json_response
@require_user
def set_playback_data(request):
    comment = None

    if 'uuid' not in request.POST:
        try:
            comment_id = request.POST['comment_id']
        except KeyError:
            raise ServiceError("Missing comment ID.")

        comment = get_object_or_404(QuestComment, id=comment_id)

        if request.user.id != comment.author.id:
            raise ServiceError("Can't upload playback data to a drawing you didn't create.")

    if 'playback_plist_data' in request.FILES:
        #plist = readPlistFromBytes(b''.join(request.FILES.get('playback_plist_data').chunks()))
        plist = readPlist(request.FILES['playback_plist_data'])
        playback_data = json.backend_dumps(plist)
    elif 'playback_data' in request.FILES:
        playback_data = u''.join(request.FILES.get('playback_data').chunks())
    else:
        playback_data = request.POST['playback_data']

    if comment is not None:
        save_playback_data(playback_data, comment=comment)
    else:
        save_playback_data(playback_data, uuid=request.POST['uuid'])


urlpatterns += patterns ('',
    url(r'^set_playback_data$', set_playback_data),
)


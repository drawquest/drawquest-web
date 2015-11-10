from django.shortcuts import get_object_or_404
from raven.contrib.django.raven_compat.models import client
import requests.exceptions

from canvas.exceptions import ServiceError
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.tumblr import models

urlpatterns = []
api = api_decorator(urlpatterns)

@api('post_photo')
@require_user
def tumblr_post_photo(request, access_token, access_token_secret, blog_hostname, comment_id):
    comment = get_object_or_404(QuestComment, id=comment_id)

    try:
        models.post_photo(request.user, blog_hostname, comment)
    except requests.exceptions.HTTPError as e:
        client.captureException()
        raise ServiceError("Error posting to Tumblr.")


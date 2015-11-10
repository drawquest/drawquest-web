from django.shortcuts import get_object_or_404

from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.star_gallery import models


urlpatterns = []
api = api_decorator(urlpatterns)

@api('starred_comments_gallery')
def starred_comments_gallery(request, username, offset='top', direction='next'):
    user = get_object_or_404(User, username=username)
    comments, pagination = models.starred_comments_gallery(user, offset=offset, direction=direction)
    return {
        'comments': comments,
        'user': user.details(),
    }


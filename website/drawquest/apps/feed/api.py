from canvas.view_guards import require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.feed.redis_models import feed_comments_for_user


urlpatterns = []
api = api_decorator(urlpatterns)


@api('followee_comments')
@require_user
def feed_items(request, offset='top', direction='next'):
    comments, pagination = feed_comments_for_user(request.user, offset=offset, direction=direction, viewer=request.user)

    return {
        'comments': comments,
        'pagination': pagination,
    }


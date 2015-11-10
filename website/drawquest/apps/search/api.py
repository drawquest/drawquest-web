from django.shortcuts import get_object_or_404
from haystack.constants import DJANGO_ID
from haystack.inputs import AutoQuery, Clean
from haystack.query import SearchQuerySet

from canvas.models import UserRedis
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest import knobs
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.details_models import UserDetails
from drawquest.apps.drawquest_auth.models import User


urlpatterns = []
api = api_decorator(urlpatterns)

@api('users')
def search_users(request, query):
    try:
        query.decode('ascii')
    except UnicodeEncodeError:
        return {'users': []}

    if len(query.strip()) > 20: # Some fudge here since we have fuzzy matching.
        return {'users': []}

    sqs = SearchQuerySet()
    conn = sqs.query.backend.conn

    hits = conn.search({
        'from': 0,
        'size': knobs.SEARCH_RESULTS_PER_PAGE,
        'query': {
            'text': {
                'text': sqs.query.clean(query),
            },
        },
    })['hits']['hits']

    user_ids = [long(hit['_source'][DJANGO_ID]) for hit in hits[:knobs.SEARCH_RESULTS_PER_PAGE]]

    try:
        exact_match = User.objects.get(username=query, is_active=True)
        try:
            user_ids.remove(exact_match.id)
        except ValueError:
            pass
        user_ids.insert(0, exact_match.id)
    except User.DoesNotExist:
        pass

    users = []
    for user_id in user_ids:
        user_redis = UserRedis(user_id)

        #TODO instead of hacking this on here, have a new Details subclass.
        result = {'user': UserDetails.from_id(user_id).to_client()}
        result['follower_count'] = user_redis.new_followers.zcard()
        result['following_count'] = user_redis.new_following.zcard()

        if request.user.is_authenticated() and request.user.id != user_id:
            result['viewer_is_following'] = request.user.is_following(user_id)

        users.append(result)

    return {
        'users': users,
    }


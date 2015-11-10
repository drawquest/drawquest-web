from canvas.cache_patterns import CachedCall
from drawquest import knobs
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.drawquest_auth.details_models import UserDetails
from drawquest.pagination import FakePaginator


def _sorted(users):
    return sorted(users, key=lambda user: user.username.lower())

def _for_viewer(users, viewer=None):
    if viewer is None or not viewer.is_authenticated():
        return users

    following = [int(id_) for id_ in viewer.redis.new_following.zrange(0, -1)]

    for user in users:
        user.viewer_is_following = user.id in following

    return users

def _paginate(redis_obj, offset, request=None):
    '''
    items should already start at the proper offset.
    '''
    if offset == 'top':
        items = redis_obj.zrevrange(0, knobs.FOLLOWERS_PER_PAGE, withscores=True)
    else:
        items = redis_obj.zrevrangebyscore('({}'.format(offset), '-inf',
                                           start=0,
                                           num=knobs.FOLLOWERS_PER_PAGE,
                                           withscores=True)

    try:
        next_offset = items[-1][1]
        next_offset = next_offset.__repr__()
    except IndexError:
        next_offset = None

    items = [item for item, ts in items]

    pagination = FakePaginator(items, offset=offset, next_offset=next_offset)

    return items, pagination

def followers(user, viewer=None, offset='top', direction='next', request=None):
    """ The users who are following `user`. """
    if direction != 'next':
        raise ValueError("Follwers only supports 'next' - scrolling in one direction.")

    if request is None or (request.idiom == 'iPad' and request.app_version_tuple <= (3, 1)):
        user_ids = user.redis.new_followers.zrevrange(0, -1)
        pagination = None
    else:
        user_ids, pagination = _paginate(user.redis.new_followers, offset, request=request)

    users = UserDetails.from_ids(user_ids)

    if request is None or request.app_version_tuple < (3, 0):
        users = _sorted(users)

    return _for_viewer(users, viewer=viewer), pagination

def following(user, viewer=None, offset='top', direction='next', request=None):
    """ The users that `user` is following. """
    if direction != 'next':
        raise ValueError("Following only supports 'next' - scrolling in one direction.")

    if request is None or (request.idiom == 'iPad' and request.app_version_tuple <= (3, 1)):
        user_ids = user.redis.new_following.zrange(0, -1)
        pagination = None
    else:
        user_ids, pagination = _paginate(user.redis.new_following, offset, request=request)

    users = UserDetails.from_ids(user_ids)

    if request is None or request.app_version_tuple < (3, 0):
        users = _sorted(users)

    return _for_viewer(users, viewer=viewer), pagination

def counts(user):
    return {
        'followers': user.redis.new_followers.zcard(),
        'following': user.redis.new_following.zcard(),
    }


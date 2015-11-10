from drawquest.apps.feed.redis_models import visible_in_feed
from canvas import knobs
from canvas.redis_models import RealtimeChannel


def updates_channel(followed_user):
    if hasattr(followed_user, 'id'):
        followed_user = followed_user.id
    return RealtimeChannel('fu:{}'.format(followed_user), 20)

def publish_new_comment(new_comment):
    from canvas.models import UserRedis

    if not visible_in_feed({'comment': new_comment.details(), 'type': 'comment'}):
        return

    author = new_comment.author

    # Bump unseen counts.
    for user_id in author.redis.new_followers.zrange(0, -1):
        user_redis = UserRedis(user_id)
        user_redis.user_kv.hincrby('feed_unseen', 1)

    updates_channel(author).publish({'comment': new_comment.id, 'type': 'comment'})


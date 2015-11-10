import drawquest.apps.feed.realtime

def realtime_feed_context(request):
    if not request.user.is_authenticated():
        return {}

    followees = request.user.redis.new_following.zrange(0, -1)
    feed_following_channels = [drawquest.apps.feed.realtime.updates_channel(followee_id).sync()
                               for followee_id in followees]

    return {
        'feed_following_channels': feed_following_channels,
        'feed_unseen': int(request.user.kv.feed_unseen.get() or 0),
    }


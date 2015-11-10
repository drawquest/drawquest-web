from website.apps.activity.base_activity import BaseActivity


class WelcomeActivity(BaseActivity):
    TYPE = 'welcome'


class StarredActivity(BaseActivity):
    TYPE = 'starred'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_sticker(cls, actor, comment_sticker):
        comment = comment_sticker.comment
        comment_details = comment_sticker.comment.details()
        data = {
            'thumbnail_url': comment_details.reply_content.get_absolute_url_for_image_type('activity'),
            'comment_id': comment_details.id,
            'quest_id': comment.parent_comment_id,
        }
        return cls(data, actor=actor)


class PlaybackActivity(BaseActivity):
    TYPE = 'playback'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_comment(cls, actor, comment):
        comment_details = comment.details()
        data = {
            'thumbnail_url': comment_details.reply_content.get_absolute_url_for_image_type('activity'),
            'comment_id': comment_details.id,
            'quest_id': comment.parent_comment_id,
        }
        return cls(data, actor=actor)


class FeaturedInExploreActivity(BaseActivity):
    TYPE = 'featured_in_explore'
    FORCE_ANONYMOUS = False
    APP_VERSION = (2,0)

    @classmethod
    def from_comment(cls, actor, comment):
        comment_details = comment.details()
        data = {
            'thumbnail_url': comment_details.reply_content.get_absolute_url_for_image_type('activity'),
            'comment_id': comment_details.id,
        }
        return cls(data, actor=actor)


class FolloweePostedActivity(BaseActivity):
    TYPE = 'followee_posted'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_comment(cls, actor, comment):
        from website.apps.activity.models import Activity, ACTIVITY_TYPE_IDS

        comment_details = comment.details()

        data = {
            'thumbnail_url': comment_details.reply_content.get_absolute_url_for_image_type('activity'),
            'comment_id': comment_details.id,
            'quest_id': comment.parent_comment_id,
            'ugq': comment.parent_comment.ugq,
        }

        # Prime the Activity DB instance, to be shared across recipients.
        key = comment_details.id
        try:
            db_activity = Activity.objects.get(activity_type=ACTIVITY_TYPE_IDS[cls.TYPE], key=key)
            data['id'] = db_activity.id
        except Activity.DoesNotExist:
            pass

        return cls(data, actor=actor)


class FolloweeCreatedUgqActivity(BaseActivity):
    TYPE = 'followee_created_ugq'
    FORCE_ANONYMOUS = False

    @classmethod
    def from_quest(cls, actor, quest):
        from website.apps.activity.models import Activity, ACTIVITY_TYPE_IDS

        quest_details = quest.details()

        data = {
            'quest_id': quest.id,
        }

        if quest_details.reply_content:
            data['thumbnail_url'] = quest_details.reply_content.get_absolute_url_for_image_type('activity')

        # Prime the Activity DB instance, to be shared across recipients.
        key = quest_details.id
        try:
            db_activity = Activity.objects.get(activity_type=ACTIVITY_TYPE_IDS[cls.TYPE], key=key)
            data['id'] = db_activity.id
        except Activity.DoesNotExist:
            pass

        return cls(data, actor=actor)


class FacebookFriendJoinedActivity(BaseActivity):
    TYPE = 'facebook_friend_joined'
    FORCE_ANONYMOUS = False
    APP_VERSION = (2,0)

    @classmethod
    def from_actor(cls, actor):
        return cls(data={
            'name': u'{} {}'.format(actor.facebookuser.first_name, actor.facebookuser.last_name),
        }, actor=actor)


class TwitterFriendJoinedActivity(BaseActivity):
    TYPE = 'twitter_friend_joined'
    FORCE_ANONYMOUS = False
    APP_VERSION = (2,0)

    @classmethod
    def from_actor(cls, actor):
        return cls(data={
            'name': actor.twitteruser.name,
            'twitter_screen_name': actor.twitteruser.screen_name,
        }, actor=actor)


class EmailFriendJoinedActivity(BaseActivity):
    TYPE = 'email_friend_joined'
    FORCE_ANONYMOUS = False
    APP_VERSION = (2,0)


class NewColorAlertActivity(BaseActivity):
    TYPE = 'new_color_alert'
    FORCE_ANONYMOUS = False
    APP_VERSION = (2,0,2)

    @classmethod
    def with_message(cls, message, color_alert_version):
        return cls(data={
            'color_alert_version': color_alert_version,
            'message': message,
        })


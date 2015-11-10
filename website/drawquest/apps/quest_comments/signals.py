from django.db.models.signals import post_save

import canvas.signals
from drawquest.apps.quest_comments.api import invalidate_user_comments
from drawquest.apps.quest_comments.models import QuestComment


canvas.signals.visibility_changed.connect(
    lambda sender, instance, **kwargs: invalidate_user_comments(instance),
    dispatch_uid='user_comments_visibility_changed', weak=False
)


def invalidate_quest_comments(sender, instance, **kwargs):
    from drawquest.apps.quest_comments import api

    api.quest_comments.delete_cache(None, instance.parent_comment_id)
    invalidate_user_comments(instance)

post_save.connect(invalidate_quest_comments, sender=QuestComment, dispatch_uid='post_save_for_quest_comments_api')

canvas.signals.visibility_changed.connect(
    invalidate_quest_comments, dispatch_uid='quest_comments_visibility_changed'
)


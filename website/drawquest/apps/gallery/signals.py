from django.db.models.signals import post_save

from drawquest import knobs
from drawquest.apps.quest_comments.models import QuestComment


def invalidate_top_gallery_comments(sender, instance, **kwargs):
    from drawquest.apps.gallery.models import top_gallery_comment_ids
    from drawquest.apps.quests.models import Quest

    quest = Quest.all_objects.get(id=instance.parent_comment_id)

    if quest.drawing_count() < knobs.TOP_GALLERY_SIZE_BEFORE_CACHING:
        top_gallery_comment_ids.delete_cache(quest)

post_save.connect(invalidate_top_gallery_comments, sender=QuestComment, dispatch_uid='post_save_for_quest_comment_top_gallery_comments')


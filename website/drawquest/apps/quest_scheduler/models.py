from django.shortcuts import get_object_or_404, Http404

from canvas.models import get_mapping_id_from_short_id
from drawquest.apps.quests.models import Quest, ScheduledQuest


class QuestPreview(object):
    def __init__(self, quest):
        self.quest = quest
        self.curator = ""
        self.timestamp = None
        self.sort = None
        self.scheduled_quest_id = None

    @classmethod
    def get_by_short_id(cls, short_id):
        try:
            mapping_id = get_mapping_id_from_short_id(short_id)
        except ValueError:
            raise Http404
        quest = get_object_or_404(Quest.published, id=mapping_id)
        return cls.get_from_quest(quest)

    @classmethod
    def get_from_quest(cls, quest):
        return cls(quest.thread.op.details())

    @classmethod
    def get_from_scheduled_quest(cls, scheduled_quest):
        preview = cls.get_from_quest(scheduled_quest.quest)
        preview.curator = getattr(scheduled_quest.curator, 'username', '')
        preview.timestamp = scheduled_quest.timestamp
        preview.sort = scheduled_quest.sort
        preview.scheduled_quest_id = scheduled_quest.id
        return preview


def scheduled_quest_previews():
    return [QuestPreview.get_from_scheduled_quest(st) for st in ScheduledQuest.unarchived()]

def suggested_quests():
    #scheduled_ids = ScheduledQuest.objects.all().values_list('quest_id', flat=True)
    scheduled = ScheduledQuest.objects.all()

    quests = Quest.public.filter(parent_comment__isnull=True, ugq=False)
    quests = quests.exclude(scheduledquest__in=scheduled)
    quests = quests.order_by('-timestamp')
    quests = quests[:50]

    return [QuestPreview.get_from_quest(quest) for quest in quests]


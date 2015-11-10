from datetime import datetime, timedelta
from time import time

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import Quest
from drawquest.apps.quests.top import top_quests_buffer


class Command(BaseCommand):
    args = ''
    help = 'Update quest scores for the top quests view.'

    def handle(self, *args, **options):
        start = time()
        updates = 0

        for quest_id in Quest.objects.all().values_list('id', flat=True):
            updates += 1
            quest = Quest.objects.get(id=quest_id)
            print quest.title
            quest.update_score()

        print "Scores updated. Rows updated: %s Total elapsed time: %0.2fs" % (updates, (time() - start))



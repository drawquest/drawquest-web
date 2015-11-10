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

        def flatten(list_of_lists):
            return set([int(item) for sublist in list_of_lists for item in sublist])

        quest_ids = [int(id_) for id_ in top_quests_buffer[:]]
        
        for quest in Quest.all_objects.in_bulk_list(quest_ids):
            updates += 1
            quest.update_score()

        print "Scores updated. Rows updated: %s Total elapsed time: %0.2fs" % (updates, (time() - start))


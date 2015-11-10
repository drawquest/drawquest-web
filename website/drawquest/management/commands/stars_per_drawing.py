import datetime
import time

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count

from canvas.notifications.actions import Actions
from drawquest import knobs, economy
from drawquest.apps.quests.models import Quest, ScheduledQuest
from drawquest.apps.drawquest_auth.models import User
from canvas.models import UserInfo, Visibility
from drawquest.apps.quest_comments.models import QuestComment


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        month_ago = time.time() - (60*60*24*7*4)
        comments = QuestComment.objects.filter(timestamp__gte=month_ago)
        print '{} drawings in the given time period'.format(comments.count())
        comments = comments.filter(visibility=Visibility.PUBLIC)
        print '{} visible drawings in the given time period'.format(comments.count())

        stars_per = comments.annotate(num_stars=Count('stickers')).aggregate(Avg('num_stars'))['num_stars__avg']
        print '{} stars per drawing in the given time period'.format(stars_per)


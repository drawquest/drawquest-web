import datetime

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count

from canvas.notifications.actions import Actions
from drawquest import knobs, economy
from drawquest.apps.quests.models import Quest, ScheduledQuest
from drawquest.apps.drawquest_auth.models import User
from canvas.models import UserInfo


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        trusted = UserInfo.objects.filter(trusted=True)
        print '{} trusted users'.format(trusted.count())

        comments_per = trusted.annotate(num_comments=Count('user__comments')).aggregate(Avg('num_comments'))['num_comments__avg']
        print '{} comments per trusted user'.format(comments_per)


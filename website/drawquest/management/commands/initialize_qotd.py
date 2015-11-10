import datetime

from django.core.management.base import BaseCommand

from canvas.notifications.actions import Actions
from drawquest import knobs, economy
from drawquest.apps.quests.models import Quest, ScheduledQuest


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        if ScheduledQuest.objects.count():
            print "You've already got a quest of the day, unless something went very wrong."
            return

        try:
            quest = Quest.objects.all()[0]
        except IndexError:
            print "Please create a quest first by visiting http://dq.savnac.com/admin/post_thread"
            return

        scheduled_quest = ScheduledQuest.get_or_create(quest)
        scheduled_quest.set_as_current_quest()


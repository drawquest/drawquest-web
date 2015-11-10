import datetime

from django.core.management.base import BaseCommand

from canvas.notifications.actions import Actions
from drawquest import knobs, economy
from drawquest.apps.explore.models import preloaded_explore_comment_ids
from drawquest.apps.quest_comments.models import QuestComment


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        for comment_id in preloaded_explore_comment_ids():
            comment = QuestComment.objects.get(id=comment_id)
            author = comment.author
            print author.username
            Actions.featured_in_explore(author, comment, defer=False)
            economy.credit(author, knobs.REWARDS['featured_in_explore'])


import datetime

from django.core.management.base import BaseCommand
from drawquest.apps.explore.models import preload_explore_comment_ids


class Command(BaseCommand):
    args = ''
    help = 'Rolls over the explore page comments to the last 24 hours.'

    def handle(self, *args, **options):
        preload_explore_comment_ids()


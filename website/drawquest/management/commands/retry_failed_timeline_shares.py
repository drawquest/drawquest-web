import datetime

from django.core.management.base import BaseCommand

from drawquest.apps.timeline.models import PendingTimelineShare
from canvas.exceptions import ServiceError


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        for pending_share in PendingTimelineShare.objects.all():
            try:
                pending_share.retry()
            except ServiceError as e:
                print u'User {}: {}'.format(pending_share.user.username, e.message)


import datetime

from django.core.management.base import BaseCommand
from matplotlib import pyplot

from drawquest.apps.drawquest_auth.models import User
from drawquest import knobs, economy


class Command(BaseCommand):
    args = ''
    help = ''

    def handle(self, *args, **options):
        balances = []

        for user in User.objects.filter(date_joined__gte=datetime.datetime.now() - datetime.timedelta(days=90)):
            if user.comments.count() < 2:
                continue
            balances.append(economy.balance(user))

        figures = {'count': 0}

        def hist(bins):
            figures['count'] += 1
            pyplot.figure(figures['count'])
            pyplot.hist(balances, bins=bins, facecolor='green', alpha=0.75)
            pyplot.xlabel('Coins')
            pyplot.ylabel('User count')
            pyplot.suptitle(r'Coin balances')
            pyplot.grid(True)
            pyplot.savefig('/home/ubuntu/graphs/{}.svg'.format(figures['count']), dpi=180)

        hist(range(0, 101, 1))
        hist(range(0, 301, 5))
        hist(range(0, 1001, 10))
        hist(range(1001, 10000, 100))


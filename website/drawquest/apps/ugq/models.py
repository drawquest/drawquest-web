import re

from django.db import models

from canvas.models import Visibility
from canvas.cache_patterns import CachedCall
from drawquest import knobs
from drawquest.apps.quests.details_models import QuestDetails
from drawquest.apps.quests.models import Quest
from drawquest.pagination import Paginator


def ugq_by_user(user, offset='top', direction='next', viewer=None):
    quests = Quest.objects.filter(author=user, ugq=True)

    if viewer is not None and viewer.is_authenticated():
        quests = quests.exclude(flags__user=viewer)

    quests = quests.order_by('-id')

    pagination = Paginator(quests, knobs.QUESTS_PER_PAGE, offset=offset, direction=direction)
    quests = pagination.items
    quests = CachedCall.queryset_details(quests)

    return quests, pagination

def autocurate_for_flag_words(quest):
    def curate():
        quest.visibility = Visibility.CURATED
        quest.save()
        quest.visibility_changed()

    for word in knobs.FLAG_WORDS:
        if re.search(r'\b{}\b'.format(word), quest.title, flags=re.IGNORECASE):
            curate()
            return

    for word in knobs.FLAG_WORD_FRAGMENTS:
        if re.search(word, quest.title, flags=re.IGNORECASE):
            curate()
            return


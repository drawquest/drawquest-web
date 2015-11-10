import time

from canvas.models import Visibility
from canvas.redis_models import redis, RedisLastBumpedBuffer
from drawquest import knobs
from drawquest.apps.quests.details_models import QuestDetails


top_quests_buffer = RedisLastBumpedBuffer('top_quests', 500)

def get_quest_score(quest):
    try:
        details = quest.details()
    except AttributeError:
        details = quest

    if not quest.ugq and not quest.scheduledquest_set.exists():
        return -1

    visibility = getattr(details, 'visibility', None)
    if visibility in Visibility.invisible_choices or visibility == Visibility.CURATED:
        return -1

    first_appeared_on = quest.first_appeared_on()

    if first_appeared_on is None:
        return -1

    tdelta = time.time() - first_appeared_on + 10 * 60
    weight = ((tdelta ** 1.9) if tdelta > 0 else 1)
    pop_score = details.drawing_count

    if quest.ugq:
        if time.time() - first_appeared_on < 60*5:
            pop_score = max(1.0, pop_score)

        if time.time() - first_appeared_on > 60*3:
            weight *= 0.9
        else:
            weight *= 1.0

    return pop_score * 1000000 / weight

def _top_quest_ids(viewer=None):
    ids = [int(id_) for id_ in top_quests_buffer[:knobs.TOP_QUESTS_SIZE]]

    if viewer is not None and viewer.is_authenticated():
        flagged_ids = Quest.objects.filter(flags__user=viewer).values_list('id', flat=True)
        ids = [id_ for id_ in ids if id_ not in flagged_ids]

    return ids

def top_quest_details(viewer=None):
    return QuestDetails.from_ids(_top_quest_ids(viewer=viewer))

def top_quests(viewer=None):
    from drawquest.apps.quests.models import Quest

    return Quest.objects.in_bulk_list(_top_quest_ids(viewer=viewer))


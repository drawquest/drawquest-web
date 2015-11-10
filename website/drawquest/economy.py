from django.shortcuts import get_object_or_404

from canvas.exceptions import ServiceError, ValidationError
from canvas.economy import InvalidPurchase
from drawquest import knobs
from drawquest.apps.palettes.models import get_palette_by_name, all_palettes, Color, ColorPack
from drawquest.apps.brushes.models import Brush
from drawquest.apps.drawquest_auth.models import User
from drawquest.signals import balance_changed


def balance(user):
    return int(user.kv.stickers.currency.get() or 0)

def _adjust_balance(user, amount):
    if amount == 0:
        return

    if amount > 0:
        user.kv.stickers.currency.increment(amount)
    else:
        result = user.kv.stickers.currency.increment_ifsufficient(amount)

        if not result['success']:
            raise InvalidPurchase("Insufficient balance.")

    balance_changed.send(None, user=user)

    publish_balance(user)

def publish_balance(user):
    user.redis.coin_channel.publish({'balance': balance(user)})

def credit(user, amount):
    _adjust_balance(user, amount)

def debit(user, amount):
    _adjust_balance(user, -amount)

def credit_first_quest(user):
    credit(user, knobs.REWARDS['first_quest'])

def credit_quest_of_the_day_completion(user):
    credit(user, knobs.REWARDS['quest_of_the_day'])

def credit_archived_quest_completion(user):
    credit(user, knobs.REWARDS['archived_quest'])

def credit_personal_share(user):
    credit(user, knobs.REWARDS['personal_share'])

def credit_personal_twitter_share(user):
    credit(user, knobs.REWARDS['personal_twitter_share'])

def credit_streak(user, streak):
    credit(user, knobs.REWARDS['streak_{}'.format(streak)])

def credit_star(user):
    user.kv.stickers_received.increment(1)
    credit(user, knobs.REWARDS['star'])

def _purchase_palette_item(user, item_cls, item_id, id_field='id'):
    item = get_object_or_404(item_cls, **{id_field: item_id})

    if item.owners.filter(id=user.id).exists():
        raise InvalidPurchase("You've already bought this.")

    if not item.is_for_sale:
        raise InvalidPurchase("Sorry, this item isn't for sale anymore.")

    debit(user, item.cost)
    item.unlock_for_user(user)

def purchase_color(user, color_id):
    _purchase_palette_item(user, Color, color_id)

def purchase_color_pack(user, color_pack_id):
    _purchase_palette_item(user, ColorPack, color_pack_id)

def purchase_brush(user, color_pack_id):
    _purchase_palette_item(user, Brush, color_pack_id, id_field='canonical_name')

# DEPRECATED.
def purchase_palette(user, palette):
    if isinstance(palette, basestring):
        palette = get_palette_by_name(palette_name)

    if palette in user.redis.palettes:
        raise InvalidPurchase("You've already bought this palette.")

    debit(user, palette.cost)
    user.redis.palettes.unlock(palette)


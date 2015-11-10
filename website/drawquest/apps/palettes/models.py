import colorsys
import itertools

from cachecow.decorators import cached_function
from django.db import models
from django.db.models import Q

from canvas.models import BaseCanvasModel
from canvas import json, bgwork
from canvas.redis_models import redis, RedisSet
from drawquest import knobs
from drawquest.activities import NewColorAlertActivity
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.push_notifications.models import push_notification
from drawquest.shop_utils import ShopMixin


DEFAULT_COLOR_COST = 10


def _legacy_palette_names(user):
    return [palette.name for palette in user.redis.palettes]


class ColorPack(BaseCanvasModel, ShopMixin):
    owners = models.ManyToManyField(User)

    colors = models.ManyToManyField('Color')

    ordinal = models.IntegerField()

    label = models.CharField(max_length=50, blank=False, db_index=False)
    cost = models.IntegerField(blank=False)
    is_for_sale = models.BooleanField(default=False)
    is_new = models.BooleanField(default=True)
    sale_text = models.CharField(max_length=50, blank=True, db_index=False)

    legacy_palette_name = models.CharField(max_length=20, blank=True, unique=True)

    class Meta(object):
        ordering = ['ordinal']

    @classmethod
    def visible_in_shop(cls, **kwargs):
        return cls.objects.filter(is_for_sale=True)

    @classmethod
    def for_user(cls, user):
        filter_query = Q(owners=user)

        if user.is_authenticated():
            palette_names = _legacy_palette_names(user)

            if palette_names:
                filter_query |= Q(legacy_palette_name__in=palette_names)

        return cls.objects.filter(filter_query)

    def to_client(self, viewer=None):
        colors = list(self.colors.all())

        if viewer is not None and viewer.is_authenticated():
            self._add_owned_by_viewer_field(Color, colors, viewer)

        ret = {
            'id': self.id,
            'label': self.label,
            'colors': colors,
            'cost': self.cost,
            'is_for_sale': self.is_for_sale,
            'is_new': self.is_for_sale,
            'sale_text': self.sale_text,
        }

        if hasattr(self, 'owned_by_viewer'):
            ret['owned_by_viewer'] = self.owned_by_viewer

            if viewer is not None:
                viewer_color_ids = Color.objects.filter(owners=viewer).values_list('id', flat=True)

                if (not self.owned_by_viewer
                        and all(color.id in viewer_color_ids for color in colors)):
                    ret['owned_by_viewer'] = True

        if ret.get('owned_by_viewer'):
            ret['is_new'] = False

        return ret


class Color(BaseCanvasModel, ShopMixin):
    owned_by_default = models.BooleanField(default=False, blank=True)
    owners = models.ManyToManyField(User)

    red   = models.IntegerField(blank=False)
    green = models.IntegerField(blank=False)
    blue  = models.IntegerField(blank=False)

    ordinal = models.IntegerField()

    label = models.CharField(max_length=50, blank=False, db_index=False)
    cost = models.IntegerField(blank=True, null=True)
    is_for_sale = models.BooleanField(default=False, blank=True)
    is_new = models.BooleanField(default=True, blank=True)

    class Meta(object):
        ordering = ['ordinal']

    #@cached_function(timeout=td(days=14), key=[
    #    ['user_colors', 'v1'],
    #    lambda username: username,
    #])
    #@classmethod
    #def _ids_for_user(cls, user):

    @classmethod
    def for_user(cls, user):
        queries = [cls.objects.filter(owned_by_default=True)]

        if user.is_authenticated():
            queries.append(cls.objects.filter(owners=user))
            queries.append(cls.objects.filter(colorpack__owners=user))

            palette_names = _legacy_palette_names(user)

            if palette_names:
                queries.append(cls.objects.filter(colorpack__legacy_palette_name__in=palette_names))
        
        ids = set(itertools.chain.from_iterable(list(q.values_list('id', flat=True)) for q in queries))

        return list(sorted(cls.objects.in_bulk_list(ids), key=lambda color: color.ordinal))

    @classmethod
    def includable_in_color_pack(cls):
        return cls.objects.filter(is_for_sale=True)

    @classmethod
    def visible_in_shop(cls, **kwargs):
        return cls.objects.filter(Q(is_for_sale=True) | Q(owned_by_default=True))

    def light_checkmark(self):
        _, lightness, _ = colorsys.rgb_to_hls(self.red / 255., self.green / 255., self.blue / 255.)
        return lightness < knobs.COLOR_CHECKMARK_LUMINOSITY_THRESHOLD

    def to_client(self, **kwargs):
        ret = {
            'id': self.id,
            'label': self.label,
            'rgb': (self.red, self.green, self.blue),
            'cost': self.cost,
            'is_for_sale': self.is_for_sale,
            'is_new': self.is_new,
            'light_checkmark': self.light_checkmark(),
            'owned_by_default': self.owned_by_default,
        }

        if self.owned_by_default:
            ret['owned_by_viewer'] = True
        elif hasattr(self, 'owned_by_viewer'):
            ret['owned_by_viewer'] = self.owned_by_viewer

        if ret.get('owned_by_viewer'):
            ret['is_new'] = False

        return ret

def new_color_alert(message, color_packs_header, colors_header):
    version = int(redis.incr('color_alert_version'))

    push_notification('new_color_alert', message,
                      extra_metadata={'color_alert_version': version})

    activity_item = NewColorAlertActivity.with_message(message, version)

    @bgwork.defer
    def broadcast_to_activity_streams():
        for user in User.objects.all():
            user.redis.activity_stream.push(activity_item)
            user.redis.iphone_activity_stream.push(activity_item)


#
#
# LEGACY:
#
#

class LegacyColor(object):
    def __init__(self, rgb=None, index=None, cost=DEFAULT_COLOR_COST):
        self.rgb = rgb
        self.index = index
        self.cost = cost

    def to_client(self, **kwargs):
        ret = {
            'rgb': self.rgb,
            'cost': self.cost,
        }

        if self.index is not None:
            ret['index'] = self.index

        return ret


class Palette(object):
    def __init__(self, id_, name, human_readable_name, cost, colors, min_app_version=None):
        """
        `colors` is a list of Color instances.
        """
        self.id = id_
        self.name = name
        self.human_readable_name = human_readable_name
        self.colors = colors
        self.cost = cost
        self.min_app_version = min_app_version

    def __repr__(self):
        return self.name

    def available_to_app_version(self, version):
        if self.min_app_version is None:
            return True

        if version is None:
            return False

        if isinstance(version, basestring):
            version = tuple(int(v) for v in version.split('.'))

        return self.min_app_version <= version

    def to_client(self, **kwargs):
        return {
            'name': self.name,
            'human_readable_name': self.human_readable_name,
            'colors': self.colors,
            'cost': self.cost,
        }

def _colors(*rgbs):
    return [LegacyColor(rgb, index=idx) for (idx, rgb) in rgbs]

DEFAULT_PALETTE = Palette(0, 'default', 'Default', 0,
                          _colors(
                              (390,   (255,255,255)),
                              (410,   (184,182,181)),
                              ( 10,   (74,74,74)),
                              (180,   (108,214,116)),
                              (140,   (255,228,92)),
                              (120,   (248,172,85)),
                              ( 60,   (233,90,92)),
                              (340,   (124,130,255)),
                              (230,   (134,213,255)),
                              (375,   (255,228,177)),
                              (200,   (36,113,247)),
                              (355,   (156,103,95)),
                          ))


PALETTE_COST = 50

_legacy_purchasable_palettes = [
    Palette(8, 'camo', 'Camo', PALETTE_COST,
            _colors(
                (356,     (180,152,115)),
                (357,     (163,107,62)),
                (171,     (107,127,53)),
                (351,     (109,75,47)),
            ), min_app_version=(1,0,3,)),
    Palette(9, 'day_glowz', 'Day Glowz', PALETTE_COST,
            _colors(
                (141,     (255,253,69)),
                (185,     (0,255,48)),
                (245,     (0,255,210)),
                (335,     (255,9,235)),
            ), min_app_version=(1,0,3,)),
    Palette(1, 'vintage_rainbow', 'Vintage Rainbow', PALETTE_COST,
            _colors(
                ( 60,     (163,53,14)),
                (100,     (242,136,0)),
                (150,     (24,200,38)),
                (220,     (44,154,213)),
                (300,     (136,60,237))
            )),
    Palette(2, 'winter_hues', 'Winter Hues', PALETTE_COST,
            _colors(
                (280,     (221,251,253)),
                (400,     (239,239,239)),
                (195,     (206,225,214)),
                (170,     (59,121,77)),
                ( 50,     (118,0,0)),
            )),
    Palette(3, 'candy', 'Candy', PALETTE_COST,
            _colors(
                ( 80,     (254,67,101)),
                ( 90,     (255,171,187)),
                (190,     (150,255,171)),
                (240,     (18,238,255)),
            )),
    Palette(4, 'humane', 'Humane', PALETTE_COST,
            _colors(
                (380,     (255,233,215)),
                (370,     (255,224,214)),
                (360,     (241,189,171)),
                (350,     (87,37,30)),
            )),
    Palette(5, 'dawn', 'Dawn', PALETTE_COST,
            _colors(
                (320,     (91,35,105)),
                (330,     (161,28,71)),
                ( 40,     (235,30,37)),
                (110,     (255,161,0)),
                (130,     (255,227,0)),
            )),
    Palette(6, 'sky_shades', 'Sky Shades', PALETTE_COST,
            _colors(
                (210,     (30,66,176)),
                (250,     (139,220,255)),
                (270,     (212,242,255)),
                (260,     (182,216,230)),
            )),
    Palette(7, 'midnight', 'Midnight', PALETTE_COST,
            _colors(
                (420,     (0,0,0)),
                (205,     (2,14,106)),
                (310,     (50,2,85)),
                (160,     (8,51,55)),
                (145,     (255,254,222)),
            )),
]

all_palettes = _legacy_purchasable_palettes + [DEFAULT_PALETTE]


def legacy_purchasable_palettes(app_version=None):
    return [palette for palette in _legacy_purchasable_palettes
            if palette.available_to_app_version(app_version)]


_palette_names = dict((palette.name, palette) for palette in _legacy_purchasable_palettes + [DEFAULT_PALETTE])
_palette_ids = dict((palette.id, palette) for palette in _legacy_purchasable_palettes + [DEFAULT_PALETTE])

def palettes_hash():
    """ Returns the sum of all RGB values in all palettes. """
    return sum([sum(p.rgb) for p in all_palettes()])

def get_palette_by_id(id_):
    if isinstance(id_, basestring):
        id_ = int(id_)

    return _palette_ids[id_]

def user_palettes(user):
    if user.is_authenticated():
        return user.redis.palettes

    return UserPalettes()

def get_palette_by_name(name):
    return _palette_names[name]


class UserPalettes(object):
    def __init__(self, user_id=None):
        self.user_id = user_id

        self._palettes = None

        if user_id:
            self._palettes = RedisSet('user:{}:palettes'.format(user_id))

    def __iter__(self):
        yield DEFAULT_PALETTE

        if self._palettes:
            for palette in self._palettes.smembers():
                yield get_palette_by_id(palette)

    def __contains__(self, palette):
        if palette.id == DEFAULT_PALETTE.id:
            return True

        return self._palettes and palette.id in self._palettes

    def to_client(self, **kwargs):
        return [palette for palette in self]

    def unlock(self, palette):
        if not self.user_id:
            raise TypeError("Cannot unlock a palette for a logged-out user.")

        if isinstance(palette, basestring):
            palette = get_palette_by_name(name)

        if palette.id == DEFAULT_PALETTE.id:
            return

        self._palettes.sadd(palette.id)


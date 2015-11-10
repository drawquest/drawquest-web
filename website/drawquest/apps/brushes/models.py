import datetime

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext, ugettext_lazy as _, pgettext

from canvas.models import BaseCanvasModel
from canvas.util import parse_version
from drawquest.apps.drawquest_auth.models import User
from drawquest.shop_utils import ShopMixin


class Brush(BaseCanvasModel, ShopMixin):
    owned_by_default = models.BooleanField(default=False)
    owners = models.ManyToManyField(User)

    ordinal = models.IntegerField()

    canonical_name = models.CharField(max_length=50, blank=False, db_index=False)
    label = models.CharField(max_length=50, blank=False, db_index=False)
    iphone_label = models.CharField(max_length=50, blank=False, db_index=False)
    description = models.CharField(max_length=300, blank=True, db_index=False)
    cost = models.IntegerField(blank=False)
    is_for_sale = models.BooleanField(default=False)
    is_new = models.BooleanField(default=True)

    red   = models.IntegerField(blank=False)
    green = models.IntegerField(blank=False)
    blue  = models.IntegerField(blank=False)

    iap_product_id = models.CharField(max_length=100, blank=True, db_index=False)

    class Meta(object):
        ordering = ['ordinal']

    @classmethod
    def visible_in_shop(cls, request=None):
        for_sale = cls.objects.filter(is_for_sale=True)

        if getattr(request, 'app_version_tuple', (0,)) < (3,):
            return for_sale.exclude(canonical_name='paintbucket')

        return for_sale

    @classmethod
    def for_global(cls):
        return [
            {'canonical_name': 'marker'},
            {'canonical_name': 'pencil'},
            {'canonical_name': 'paintbrush'},
            {'canonical_name': 'paintbucket'},
            {'canonical_name': 'eraser'},
        ]

    @classmethod
    def for_user(cls, user):
        filter_query = Q(owned_by_default=True)

        if user.is_authenticated():
            filter_query |= Q(owners=user)

            try:
                version = parse_version(user.kv.signup_app_version.get())
            except ValueError:
                version = None

            if (version is None or version <= (2,0,1)
                    or user.date_joined <= datetime.datetime(2013, 9, 27, 12, 0, 0)):
                filter_query |= Q(canonical_name='paintbrush')

        return cls.objects.filter(filter_query).distinct()

    def _localized_label(self, val):
        return {
            'Billy the Brush': ugettext('Billy the Brush'),
            'Patty the Paint Can': ugettext('Patty the Paint Can'),
            'Marker': ugettext('Marker'),
            'Pencil': ugettext('Pencil'),
            'Eraser': ugettext('Eraser'),
        }.get(val, val)

    @property
    def localized_label(self):
        return self._localized_label(self.label)

    @property
    def localized_iphone_label(self):
        return self._localized_label(self.iphone_label)

    @property
    def localized_description(self):
        return {
            'Billy is perfect for that painterly look. He also loves jam and singing in the shower.': ugettext('Billy is perfect for that painterly look. He also loves jam and singing in the shower.'),
            "Need to color the whole canvas? Patty is always happy to help out. She'll fill the entire screen with a single color.": ugettext("Need to color the whole canvas? Patty is always happy to help out. She'll fill the entire screen with a single color."),
        }.get(self.description, self.description)

    def to_client(self, viewer=None):
        ret = {
            'canonical_name': self.canonical_name,
            'label': self.localized_label,
            'iphone_label': self.localized_iphone_label,
            'description': self.localized_description,
            'rgb': (self.red, self.green, self.blue),
            'cost': self.cost,
            'is_for_sale': self.is_for_sale,
            'is_new': self.is_for_sale,
        }

        if self.iap_product_id:
            ret['iap_product_id'] = self.iap_product_id

        if hasattr(self, 'owned_by_viewer'):
            ret['owned_by_viewer'] = self.owned_by_viewer

        if ret.get('owned_by_viewer'):
            ret['is_new'] = False

        return ret


from django.shortcuts import get_object_or_404

from canvas.exceptions import ServiceError, ValidationError
from canvas.notifications.actions import Actions
from canvas.redis_models import redis
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest import economy
from drawquest.api_decorators import api_decorator
from drawquest.apps.drawquest_auth.models import User, AnonymousUser
from drawquest.apps.palettes import models


urlpatterns = []
api = api_decorator(urlpatterns)

@api('purchase_color')
def purchase_color(request, color_id):
    try:
        economy.purchase_color(request.user, color_id)
    except economy.InvalidPurchase as e:
        raise ServiceError(e.message)

    return {
        'shop_colors': list(models.Color.for_shop(viewer=request.user)),
        'user_colors': list(models.Color.for_user(request.user)),
        'color_packs': list(models.ColorPack.for_shop(viewer=request.user)),
        'balance': economy.balance(request.user),
    }

@api('purchase_color_pack')
def purchase_color_pack(request, color_pack_id):
    try:
        economy.purchase_color_pack(request.user, color_pack_id)
    except economy.InvalidPurchase as e:
        raise ServiceError(e.message)

    return {
        'shop_colors': list(models.Color.for_shop(viewer=request.user)),
        'user_colors': list(models.Color.for_user(request.user)),
        'color_packs': list(models.ColorPack.for_shop(viewer=request.user)),
        'balance': economy.balance(request.user),
    }

@api('new_color_alert')
@require_staff
def new_color_alert(request, message):
    models.new_color_alert(message)

@api('set_headers')
@require_staff
def set_headers(request, color_packs_header, colors_header):
    color_packs_header = color_packs_header or ''
    colors = colors_header or ''

    redis.set('color_packs_header', color_packs_header)
    redis.set('colors_header', colors_header)




#
# DEPRECATED:
#

@api('user_palettes')
def user_palettes(request):
    return {'palettes': models.user_palettes(request.user)}

@api('purchasable_palettes')
def purchasable_palettes(request):
    return {'palettes': models.legacy_purchasable_palettes(app_version=getattr(request, 'app_version', None))}

@api('purchase_palette')
@require_user
def purchase_palette(request, username, palette_name):
    try:
        palette = models.get_palette_by_name(palette_name)
    except KeyError:
        raise ValidationError("Invalid palette name.")

    try:
        economy.purchase_palette(request.user, palette)
    except economy.InvalidPurchase as e:
        raise ServiceError(e.message)

    return {'palettes': request.user.redis.palettes}


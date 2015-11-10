from django.shortcuts import get_object_or_404

from canvas.exceptions import ServiceError
from drawquest.api_decorators import api_decorator
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.apps.brushes import models
from drawquest import economy


urlpatterns = []
api = api_decorator(urlpatterns)

@api('purchase_brush')
def purchase_brush(request, brush_canonical_name):
    try:
        economy.purchase_brush(request.user, brush_canonical_name)
    except economy.InvalidPurchase as e:
        raise ServiceError(e.message)

    return {
        'shop_brushes': list(models.Brush.for_shop(viewer=request.user)),
        'user_brushes': list(models.Brush.for_user(request.user)),
        'balance': economy.balance(request.user),
    }


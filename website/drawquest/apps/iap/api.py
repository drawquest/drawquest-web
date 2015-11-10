from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404

from canvas.metrics import Metrics
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.util import Now
from canvas.view_guards import require_staff, require_user
from drawquest import economy
from drawquest.api_decorators import api_decorator
from drawquest.apps.brushes.models import Brush
from drawquest.apps.iap.models import IapReceipt, COIN_PRODUCTS, BRUSH_PRODUCTS, deliver_product


urlpatterns = []
api = api_decorator(urlpatterns)

@api('coin_products')
@require_user
def iap_coin_products(request):
    return {'coin_products': COIN_PRODUCTS}

@api('products')
@require_user
def iap_products(request):
    return {
        'coin_products': COIN_PRODUCTS,
        'brush_products': BRUSH_PRODUCTS,
    }

@api('process_receipt')
@require_user
def iap_process_receipt(request, receipt_data):
    """
    Verifies the receipt, and processes the purchase.
    """
    def response():
        return {
            'balance': economy.balance(request.user),
            'shop_brushes': Brush.for_shop(viewer=request.user, request=request),
        }

    #TODO To be safer against botting, the receipt_data uniqueness constraint
    # needs to be done atomically.
    if IapReceipt.objects.filter(receipt_data=receipt_data).exists():
        # Already processed this receipt, fail silently.
        return response()

    receipt = IapReceipt.objects.create(
        purchaser=request.user,
        receipt_data=receipt_data,
        timestamp=Now(),
    )

    try:
        receipt.verify()
        Metrics.receipt_verification_success.record(request)
    except ValidationError:
        Metrics.receipt_verification_error.record(request)

    if receipt.verified:
        deliver_product(request.user, receipt.product_id)

        return response()


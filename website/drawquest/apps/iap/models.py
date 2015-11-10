from socket import error as socket_error
import urllib2

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import *
from raven.contrib.django.raven_compat.models import client

from canvas import json
from canvas.models import BaseCanvasModel
from canvas.util import UnixTimestampField, Now
from drawquest import economy
from drawquest.apps.brushes.models import Brush
from drawquest.apps.drawquest_auth.models import User


COIN_PRODUCTS = dict(('as.canv.drawquest.products.coins.' + key, val) for key,val in {
    '50': {
        'amount': 50,
    },
    '150': {
        'amount': 150,
        #'description': "Save 15%!",
    },
    '400': {
        'amount': 400,
        #'description': "Save 33%!",
    },
}.items())

BRUSH_PRODUCTS = dict(('as.canv.drawquest.products.brushes.' + key, val) for key,val in {
    'paintbrush': {
        'amount': 99,
    },
    'paintbucket': {
        'amount': 99,
        'app_version': (3,),
    },
}.items()) 

def brush_products(request=None):
    return dict((key, {'amount': val['amount']})
                for key, val in BRUSH_PRODUCTS.items()
                if (not getattr(request, 'app_version_tuple', None)
                    or val.get('app_version', (0,)) <= request.app_version_tuple))

def deliver_product(user, product_id):
    try:
        product = COIN_PRODUCTS[product_id]
        economy.credit(user, product['amount'])
    except KeyError:
        product = BRUSH_PRODUCTS[product_id]
        Brush.objects.get(iap_product_id=product_id).unlock_for_user(user)


class IapReceipt(BaseCanvasModel):
    """
    See: http://developer.apple.com/library/ios/#documentation/NetworkingInternet/Conceptual/StoreKitGuide/VerifyingStoreReceipts/VerifyingStoreReceipts.html
    """
    purchaser = ForeignKey(User, db_index=True, related_name='iap_receipts')
    receipt_data = TextField()
    timestamp = UnixTimestampField()

    product_id = CharField(blank=True, max_length=256)
    version_external_identifier = CharField(blank=True, max_length=256)
    bvrs = CharField(blank=True, max_length=256)
    bid = CharField(blank=True, max_length=256)

    verified = BooleanField(default=False)

    def verify(self):
        try:
            cleaned_data = verify_receipt(self.receipt_data, user=self.purchaser)
        except ValidationError:
            self.verified = False
            self.save()
            raise

        for prop in ['bid', 'bvrs', 'product_id']:
            setattr(self, prop, cleaned_data[prop])

        # Missing in the sandbox.
        if 'version_external_identifier' in cleaned_data:
            self.version_external_identifier = cleaned_data['version_external_identifier']

        self.verified = True
        self.save()


def verify_receipt(receipt_data, user=None):
    """
    Returns the receipt data, or raises a ValidationError.
    """
    #data = json.dumps({'receipt-data': '{' + receipt_data + '}'})
    data = '{{\n "receipt-data" : "{}" \n}}'.format(receipt_data)

    def verify(url):
        tries = 3
        for try_ in range(1, tries + 1):
            try:
                req = urllib2.Request(url, data)
                resp = urllib2.urlopen(req, timeout=18) # app timeout is supposed to be 60
                return json.loads(resp.read())
            except (urllib2.URLError, socket_error) as e:
                if try_ == tries:
                    raise e

    cleaned_data = verify(settings.IAP_VERIFICATION_URL)

    # See: http://developer.apple.com/library/ios/#technotes/tn2259/_index.html
    if cleaned_data['status'] == 21007:
        cleaned_data = verify(settings.IAP_VERIFICATION_SANDBOX_URL)

    if cleaned_data['status'] != 0:
        extra = {'status': cleaned_data['status']}
        if user is not None and user.is_authenticated():
            extra['username'] = user.username
            extra['response_from_apple'] = json.dumps(cleaned_data)
        client.captureMessage('IAP receipt validation failed', extra=extra)
        raise ValidationError("Your purchase went through, but there was an error processing it. Please contact support: support@example.com")

    return cleaned_data['receipt']


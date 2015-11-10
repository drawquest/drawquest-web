# Forked from https://github.com/IanLewis/django-ses/tree/bounce_notifications
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from raven.contrib.django.raven_compat.models import client


from canvas import json
from canvas.util import logger
from canvas.view_guards import require_POST
from drawquest.apps.bounces import models
from drawquest.apps.bounces.verification import verify_bounce_message


@require_POST
@csrf_exempt
def handle_notification(request):
    """ Handle bounced emails via an SNS webhook. """
    try:
        notification = json.loads(request.body)
    except ValueError, e:
        client.captureException()
        return HttpResponseBadRequest()

    if (settings.AWS_SES_VERIFY_BOUNCE_SIGNATURES and 
            not verify_bounce_message(notification)):
        # Don't send any info back when the notification is not verified.
        logger.info('Received unverified notification: Type: %s', 
            notification.get('Type'),
            extra={'notification': notification},
        )
        return HttpResponse()

    getattr(models, 'handle_{}'.format(notification.get('Type')))(notification)

    # AWS will consider anything other than 200 to be an error response and
    # resend the SNS request. We don't need that so we return 200 here.
    return HttpResponse()


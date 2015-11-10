import datetime
import logging

from django.shortcuts import get_object_or_404

from drawquest.api_decorators import api_decorator
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from services import Services


urlpatterns = []
api = api_decorator(urlpatterns)

ios_logger = logging.getLogger('ios_logger')

@api('bulk_log')
def log(request, records):
    for record in records:
        timestamp, level, message = record
        ios_time = datetime.datetime.fromtimestamp(timestamp).isoformat()
        ios_logger.log(getattr(logging, level), message, extra={'ios_time': ios_time})


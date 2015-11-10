import time

from django.utils.translation import ugettext, ungettext
from jinja2 import Markup

from canvas.templatetags.jinja_base import (global_tag, filter_tag, render_jinja_to_string,
                                            jinja_context_tag, update_context)
from drawquest.apps.quest_comments.details_models import QuestCommentDetails
from drawquest.apps.quests.details_models import QuestDetails

@global_tag
def get_share_page_url(comment_details):
    if getattr(comment_details, 'ugq', False) or isinstance(comment_details, QuestDetails):
        obj = QuestDetails.from_id(comment_details.id)
    else:
        obj = QuestCommentDetails.from_id(comment_details.id)
    return obj.share_page_url

@global_tag
def iso_8601(timestamp):
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(timestamp))

@global_tag
def app_store_link():
    return "https://itunes.apple.com/us/app/drawquest-free-daily-drawing/id576917425?ls=1&mt=8"

@global_tag
def app_store_id():
    return "576917425"

@global_tag
def gettext(text, **kwargs):
    return Markup(ugettext(text % kwargs))


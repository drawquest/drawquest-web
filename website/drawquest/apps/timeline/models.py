import urllib

from django.conf import settings
from django.db import models
from facebook import GraphAPIError, GraphAPI
from raven.contrib.django.raven_compat.models import client

from apps.share_tracking.models import get_share_page_url_with_tracking
from canvas import bgwork
from canvas.exceptions import ServiceError
from canvas.metrics import Metrics
from canvas.models import Comment, FacebookUser, BaseCanvasModel
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.quests.models import Quest
from drawquest import economy
from drawquest.apps.drawquest_auth.models import User


class PendingTimelineShare(BaseCanvasModel):
    user = models.ForeignKey(User, null=False)
    comment = models.ForeignKey(Comment, unique=True)
    access_token = models.CharField(max_length=300)

    def retry(self, **kwargs):
        self.share(reward=False, **kwargs)

    def is_ugq(self):
        return self.comment.parent_comment_id is None

    def get_share_obj(self):
        if self.is_ugq():
            return Quest.all_objects.get(id=self.comment.id)
        else:
            return QuestComment.all_objects.get(id=self.comment.id)

    def share(self, request=None, reward=True, share_in_bgwork=True, fail_silently=True):
        if self.user.id != self.comment.author_id:
            raise ServiceError("You can't share to your timeline a drawing you didn't create.")

        try:
            self.user.facebookuser
        except FacebookUser.DoesNotExist:
            raise ServiceError("Can't share to your timeline if you haven't added your Facebook account yet.")

        quest_url = get_share_page_url_with_tracking(self.get_share_obj(), self.user, 'facebook', absolute=True)

        if reward:
            @bgwork.defer
            def rewards():
                economy.credit_personal_share(self.user)

        if self.is_ugq():
            verb = 'create'
        else:
            # Although we've renamed it to "draw", Facebook still internally refers to it as "complete".
            verb = 'complete'
        send_action = '{}:{}'.format(settings.FACEBOOK_NAMESPACE, verb)

        def do_graph_action():
            graph = GraphAPI(self.access_token)

            #if (e.error_code == 3502
            #    or "An unexpected error has occurred." in e.message):

            try:
                post_data = urllib.urlencode({'quest': quest_url})
                post_data += '&fb:explicitly_shared=true'
                graph.request('me/{}'.format(send_action), post_data=post_data)

                if request:
                    Metrics.share_to_timeline.record(request, quest=quest_url)

                self.delete()
            except GraphAPIError as e:
                if request:
                    Metrics.share_to_timeline_error.record(request, quest=quest_url)

                if fail_silently:
                    client.captureException()
                else:
                    raise e

        if share_in_bgwork:
            bgwork.defer(do_graph_action)
        else:
            do_graph_action()


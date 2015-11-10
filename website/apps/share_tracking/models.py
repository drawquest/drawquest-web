from django.conf import settings
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.db import models

from canvas import util, fact
from canvas.exceptions import ServiceError
from canvas.models import Metrics
from canvas.url_util import verify_first_party_url


class ShareTrackingUrl(models.Model):
    sharer = models.ForeignKey(User, null=True)
    timestamp = util.UnixTimestampField()
    redirect_url = models.CharField(max_length=255, blank=True)
    channel = models.CharField(max_length=64)

    @staticmethod
    def create(user, url, channel):
        if not url:
            url = ''

        verify_first_party_url(url)

        share = ShareTrackingUrl(
            sharer=user if user.is_authenticated() else None,
            redirect_url=url,
            timestamp=util.Now(),
            channel=channel
        )
        share.save()
        return share

    @property
    def url(self):
        return reverse('apps.share_tracking.views.shared_url', kwargs={'share_id': util.base36encode(self.id)})

    @property
    def absolute_url(self):
        return 'http://' + settings.DOMAIN + self.url

    @property
    def get_arg(self):
        return "s=" + util.base36encode(self.id)

    @property
    def absolute_redirect_url_with_get_arg(self):
        return self.redirect_url + '?' + self.get_arg

    def url_for_channel(self):
        if self.channel in ['tumblr', 'email', 'testing', 'twitter', 'text_message', 'flickr', 'instagram', 'clipboard']:
            return self.absolute_url
        elif self.channel in ['facebook']:
            return self.absolute_redirect_url_with_get_arg

        raise ValueError("Invalid channel.")

    def record_view(self, request):
        Metrics.share_redirect.record(
            request,
            share=self.id,
            sharer=self.sharer_id,
            share_channel=self.channel,
            share_ts=self.timestamp,
            share_redirect_url=self.redirect_url,
        )


def get_share_page_url_with_tracking(comment, sharer, channel, request=None, absolute=None):
    url = comment.get_share_page_url(absolute=absolute)
    share = ShareTrackingUrl.create(sharer, url, channel)

    if request and channel != 'testing':
        fact.record('create_share_url', request, dict(url=url, channel=channel, share=share.id))

    return share.url_for_channel()


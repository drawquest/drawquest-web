from django.core.urlresolvers import reverse
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext

from apps.client_details.models import ClientDetailsBase
from canvas import util
from canvas.cache_patterns import CachedCall
from drawquest.apps.drawquest_auth.details_models import UserDetails
from drawquest.details_models import ContentDetails


class QuestDetails(ClientDetailsBase):
    TO_CLIENT_WHITELIST = [
        'id',
        ('content', True),
        'timestamp',
        'title',
        'user',
        'comments_url',
        'author_count',
        'drawing_count',
        'attribution_username',
        'attribution_copy',
        ('attribution_avatar_url', True),
        ('attribution_avatar_urls', True),
    ]

    @classmethod
    def from_id(cls, quest_id):
        from drawquest.apps.quests.models import Quest
        return Quest.details_by_id(quest_id)()

    @classmethod
    def from_ids(cls, quest_ids):
        from drawquest.apps.quests.models import Quest
        return CachedCall.queryset_details(Quest.objects.in_bulk_list(quest_ids))

    def to_dict(self):
        return self._d

    @property
    def attribution_copy(self):
        return {
            'Submitted by:': ugettext('Submitted by:'),
        }.get(self._d.get('attribution_copy'), self._d.get('attribution_copy'))

    @property
    def content(self):
        content = self._d['content']

        if not content:
            return content

        return ContentDetails(content)

    @property
    def reply_content(self):
        """ Shim for canvas internals. """
        return self.content

    @property
    def user(self):
        from drawquest.apps.drawquest_auth.models import User

        if self.ugq:
            return UserDetails.from_id(self.author_id)

        try:
            return User.details_by_username('QuestBot')()
        except User.DoesNotExist:
            return UserDetails.from_id(self.author_id)

    @property
    def share_page_url(self):
        if not slugify(self.title):
            return '/q/' + util.base36encode(self.id)

        return reverse('quest', args=[util.base36encode(self.id), slugify(self.title)])

    @property
    def absolute_share_page_url(self):
        return 'http://example.com' + self.share_page_url


from apps.client_details.models import ClientDetailsBase
from canvas.details_models import CommentDetailsStickersMixin, CommentDetailsRealtimeMixin
from drawquest.details_models import ContentDetails
from drawquest.apps.drawquest_auth.details_models import UserDetails
from canvas import util
from canvas.cache_patterns import CachedCall


class QuestCommentDetails(ClientDetailsBase, CommentDetailsStickersMixin, CommentDetailsRealtimeMixin):
    TO_CLIENT_WHITELIST = [
        'id',
        'user',
        'timestamp',
        'content',
        'quest_id',
        'quest_title',
        'reactions',
        'star_count',
        'playback_count',
        'posted_on_quest_of_the_day',
        ('viewer_has_starred', True),
    ]

    @classmethod
    def from_id(cls, comment_id):
        from drawquest.apps.quest_comments.models import QuestComment

        return QuestComment.details_by_id(comment_id, promoter=cls)()

    @classmethod
    def from_ids(cls, comment_ids):
        from drawquest.apps.quest_comments.models import QuestComment

        return CachedCall.queryset_details(QuestComment.objects.in_bulk_list(comment_ids), promoter=cls)

    def to_dict(self):
        return self._d

    @property
    def content(self):
        return ContentDetails(self._d['content'])

    @property
    def reply_content(self):
        """ Shim for canvas internals. """
        return self.content

    @property
    def share_page_url(self):
        return '/p/' + util.base36encode(self.id)

    @property
    def absolute_share_page_url(self):
        return 'https://example.com' + self.share_page_url

    @property
    def user(self):
        if not getattr(self, '_memoized_user', None):
            self._memoized_user = UserDetails.from_id(self.author_id)

        return self._memoized_user

    @property
    def playback_count(self):
        return len([reaction for reaction in self._d['reactions']
                    if reaction['reaction_type'] == 'playback'])

    def has_viewer_starred(self, viewer):
        return any(True for reaction in self._d['reactions']
                   if (reaction['reaction_type'] == 'star'
                       and reaction['user']['id'] == viewer.id))

    def is_visible(self):
        from canvas.models import Visibility
        return Visibility.is_visible(self.visibility)


class QuestCommentExploreDetails(QuestCommentDetails):
    """
    For use in the explore page.
    """
    TO_CLIENT_WHITELIST = [
        'id',
        'user',
        'timestamp',
        'content',
        'quest_id',
        'quest_title',
        'star_count',
        'playback_count',
        'posted_on_quest_of_the_day',
        ('viewer_has_starred', True),
    ]


QuestCommentGalleryDetails = QuestCommentExploreDetails


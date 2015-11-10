from apps.client_details.models import ClientDetailsBase
from canvas.cache_patterns import CachedCall


class UserDetails(ClientDetailsBase):
    TO_CLIENT_WHITELIST = [
        'id',
        'username',
        'avatar_url',
        'avatar_urls',
        ('fb_uid', True),
        ('twitter_uid', True),
        ('viewer_is_following', True),
    ]

    @classmethod
    def from_id(cls, user_id):
        from drawquest.apps.drawquest_auth.models import User
        return User.details_by_id(user_id, promoter=cls)()

    @classmethod
    def from_ids(cls, user_ids):
        from drawquest.apps.drawquest_auth.models import User
        return CachedCall.multicall([User.details_by_id(user_id, promoter=cls)
                                     for user_id in user_ids])
    
    @property
    def web_avatar_url(self):
        return self.avatar_urls['profile']['1x']


class PrivateUserDetails(UserDetails):
    TO_CLIENT_WHITELIST = UserDetails.TO_CLIENT_WHITELIST + [
        'email',
    ]


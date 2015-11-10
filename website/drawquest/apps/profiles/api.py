from django.shortcuts import get_object_or_404
from facebook import GraphAPI, GraphAPIError
from raven.contrib.django.raven_compat.models import client

from canvas.exceptions import InvalidFacebookAccessToken
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.api_decorators import api_decorator
from drawquest.apps.twitter.models import Twitter, TwitterError, TwitterDuplicateStatusError


urlpatterns = []
api = api_decorator(urlpatterns)

@api('share_web_profile')
@require_user
def share_web_profile(request, message,
                      twitter_access_token=None, twitter_access_token_secret=None,
                      facebook_access_token=None):

    if twitter_access_token is not None and twitter_access_token_secret is not None:
        try:
            Twitter(twitter_access_token, twitter_access_token_secret).tweet(message)
        except TwitterDuplicateStatusError as e:
            pass
        except TwitterError as e:
            client.captureException()

    if facebook_access_token:
        graph = GraphAPI(facebook_access_token)

        try:
            graph.put_object('me', 'feed', message=message)
        except GraphAPIError:
            raise InvalidFacebookAccessToken("Invalid Facebook access token, please re-auth with Facebook.")
        except IOError:
            client.captureException()


from django.shortcuts import get_object_or_404, Http404

from canvas.cache_patterns import cache_page, CachedCall
from canvas.shortcuts import r2r_jinja
from canvas.view_guards import require_user
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.profiles import models
from drawquest.apps.following import models as following_models
from drawquest.apps.quest_comments.models import QuestComment


@cache_page(10)
def _profile(request, user, template='profiles/profile.html'):
    comments = QuestComment.by_author(user)

    top_comments = models.top_comments(user)

    if top_comments is None:
        comments = CachedCall.queryset_details(comments)
    else:
        comments, top_comments = CachedCall.many_queryset_details(comments, top_comments)

    follow_counts = following_models.counts(user)

    return r2r_jinja(template, {
        'target_user': user,
        'comments': comments,
        'top_comments': top_comments,
        'follower_count': follow_counts['followers'],
        'following_count': follow_counts['following'],
    }, request)

def profile(request, username):
    user = get_object_or_404(User, username=username)

    if user.kv.web_profile_privacy.get() or not user.is_active:
        raise Http404()

    return _profile(request, user)

@require_user
def profile_preview(request):
    return _profile(request, request.user, template='profiles/profile_preview.html')


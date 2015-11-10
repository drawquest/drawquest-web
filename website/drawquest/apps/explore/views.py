from canvas.shortcuts import r2r_jinja
from drawquest.apps.explore.models import explore_comment_details
from drawquest.apps.drawquest_auth.models import User


def staff_explore(request):
    ctx = {
        'comments': explore_comment_details(),
        'User': User,
    }
    return r2r_jinja('explore/staff_explore.html', ctx, request)


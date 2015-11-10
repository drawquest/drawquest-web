from django.shortcuts import get_object_or_404
from django.db.models import Q

from canvas.exceptions import ServiceError
from drawquest.api_decorators import api_decorator
from drawquest import economy
from canvas.templatetags.jinja_base import render_jinja_to_string
from canvas.view_guards import require_staff, require_user
from drawquest.apps.drawquest_auth.models import User


urlpatterns = []
api = api_decorator(urlpatterns)

@api('deactivate_user')
@require_staff
def staff_deactivate_user(request, username, email):
    user = get_object_or_404(User, username=username)

    if user.email != email:
        raise ServiceError("Given email does not match the user's email, which is {}.".format(user.email))

    user.is_active = False
    user.save()
    user.invalidate_details()

@api('rename_user')
@require_staff
def staff_rename_user(request, current_username, new_username, email):
    user = get_object_or_404(User, username=current_username)

    if user.email != email:
        raise ServiceError("Given email does not match the user's email, which is {}.".format(user.email))

    user.username = new_username
    user.save()
    user.invalidate_details()


@api('find_user_by_email')
@require_staff
def staff_find_user_by_email(request, email):
    user = get_object_or_404(User, email=email)
    return {'username': user.username, 'email': user.email}

@api('find_user_by_app_review_name')
@require_staff
def staff_find_users_by_itunes_name(request, name):
    users = User.objects.filter(Q(email__icontains=name) | Q(username__icontains=name))
    return {'users': [{'username': user.username, 'email': user.email} for user in users]}

@api('unsubscribe_email')
@require_staff
def staff_unsubscribe_email(request, email):
    user = get_object_or_404(User, email=email)
    user.kv.subscriptions.unsubscribe_from_all()

@api('trust')
@require_staff
def trust_user(request, username):
    user = get_object_or_404(User, username=username)
    user.userinfo.trust()

@api('distrust')
@require_staff
def distrust_user(request, username):
    user = get_object_or_404(User, username=username)
    user.userinfo.distrust()

@api('remove_avatar')
@require_staff
def remove_avatar(request, username):
    user = get_object_or_404(User, username=username)
    user.userinfo.avatar = None
    user.userinfo.save()
    user.invalidate_details()

@api('gift_coins')
@require_staff
def staff_gift_coins(request, username, amount):
    amount = int(amount)

    if amount > 400:
        raise ServiceError("Can't gift more than 400 at a time (sanity check).")

    user = get_object_or_404(User, username=username)
    economy.credit(user, amount)


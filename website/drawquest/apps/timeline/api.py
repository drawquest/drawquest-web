from django.shortcuts import get_object_or_404

from drawquest.api_decorators import api_decorator
from canvas.view_guards import require_staff, require_user

urlpatterns = []
api = api_decorator(urlpatterns)


from canvas.models import User
from django.db.models import *
n=User.objects.all().annotate(num_drawings=Count('comments')).aggregate(Avg('num_drawings'))
nt=User.objects.filter(userinfo__trusted=True).annotate(num_drawings=Count('comments')).aggregate(Avg('num_drawings'))
nnu=User.objects.exclude(userinfo__trusted=False).annotate(num_drawings=Count('comments')).aggregate(Avg('num_drawings'))
print n
print nt
print nnu


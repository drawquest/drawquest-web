from canvas.models import Visibility
from drawquest.apps.whitelisting.models import auto_moderate_unjudged_comments

limit = 600
orig_limit = limit
d = 0
w = 0

for ui in UserInfo.objects.filter(trusted=False, trust_changed__isnull=True).order_by('-id').select_related('user'):
    user = ui.user
    disabled = user.comments.filter(judged=True, visibility=Visibility.DISABLED).count()
    limit -= 1
    if limit < 0:
        break
    if disabled > 0:
        d += 1
        print '!',
        continue
    curated = user.comments.filter(judged=True, visibility=Visibility.CURATED).count()
    if curated <= 4:
        #print '.',
        print user.username,
        w += 1
        ui.trusted = None
        ui.save()
        auto_moderate_unjudged_comments(user)
    elif curated >= 8:
        print '*',
    else:
        print ' ',

print 'skipped {} users w disabled comments'.format(d)
print 'found {} users to become unknown'.format(w)
print 'skipped {} other users'.format(orig_limit - (w + d))


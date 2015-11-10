import datetime, time
from django.conf import settings
def unix(dt):
    return time.mktime(dt.timetuple())

launch_date = datetime.datetime(year=2013, month=7, day=11)
stars = CommentSticker.objects.filter(type_id=settings.STAR_STICKER_TYPE_ID)
period = datetime.timedelta(days=1*7)
before_launch = stars.filter(timestamp__gte=unix(launch_date - period), timestamp__lt=unix(launch_date))
after_launch = stars.filter(timestamp__gte=unix(launch_date), timestamp__lt=unix(launch_date + period))
print 'before:', before_launch.count()
print 'after:', after_launch.count()

print User.objects.filter(date_joined__gte=(launch_date - period), date_joined__lt=(launch_date)).count()
print User.objects.filter(date_joined__gte=launch_date, date_joined__lt=(launch_date + period)).count()


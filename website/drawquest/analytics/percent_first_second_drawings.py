import time
first = 0
ts = time.time() - 60*60 #hour
all_cmts = QuestComment.all_objects.filter(timestamp__gte=ts)
for q in all_cmts:
    cmts = q.author.comments.all().order_by('id')
    try:
        f=cmts[0]
        if int(q.id) == int(f.id):
            first += 1
            continue
    except IndexError:
        pass

print all_cmts.count(), 'total drawings in last hour'
print first, 'first time drawings'
print first/60., 'drawings/minute'


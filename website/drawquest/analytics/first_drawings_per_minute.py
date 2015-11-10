
first = 0
second = 0
uids=set()
for q in QuestComment.all_objects.order_by('-id')[:10000]:
    cmts = q.author.comments.all().order_by('id')
    uids.add(q.author_id)
    try:
        f=cmts[0]
        if int(q.id) == int(f.id):
            first += 1
            continue
    except IndexError:
        pass
    try:
        s=cmts[1]
        if int(q.id) == int(s.id):
            second += 1
    except IndexError:
        pass


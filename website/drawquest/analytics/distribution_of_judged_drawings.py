from collections import Counter
cnt=Counter()
for q in QuestComment.all_objects.filter(judged=True).order_by('-id')[:10000]:
    cnt[{0: 'public', 2: 'disabled', 4: 'curated'}[q.visibility]] += 1
    if q.author.is_active==False:
        cnt['banned'] += 1


for k,v in cnt.items():
    print '{}: {}'.format(k, v)



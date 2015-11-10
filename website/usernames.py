#usernames=User.objects.all().values_list('username', flat=True)
#d=dict((u.lower(),u) for u in usernames)
#with open('usernames.js', 'w') as f:
#    f.write('window.usernames = [\n')
#    for idx, pair in enumerate(d.iteritems()):
#        k, v = pair
#        if idx == len(d) - 1:
#            f.write(u'"{}"\n'.format(k,v).encode('utf8'))
#        else:
#            f.write(u'"{}",\n'.format(k,v).encode('utf8'))
#    f.write('];')

usernames=User.objects.all().values_list('username', flat=True)
usernames = sorted(usernames, key=lambda e: e.lower())
#d=dict((u.lower(),u) for u in usernames)
with open('mixed_case_usernames.js', 'w') as f:
    f.write('window.usernames = [\n')
    for idx, v in enumerate(usernames):#d.iteritems()):
        #k, v = pair
        if v.lower() == v:
            continue
        if idx == len(usernames) - 1:
            f.write(u'"{}"\n'.format(v).encode('utf8'))
        else:
            f.write(u'"{}",\n'.format(v).encode('utf8'))
    f.write('];')


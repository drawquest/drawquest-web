from configuration import aws
from drawquest.apps.quests.models import ScheduledQuest
from django.db.models import Count
import datetime
from django.core.management.base import BaseCommand
from canvas.shortcuts import r2r_jinja
from canvas.details_models import ContentDetails
from apps.canvas_auth.models import User
from canvas.redis_models import redis
import tarfile
from django.conf import settings
import os
from canvas.storage import SimpleStorageServiceFS
from canvas import util
import tempfile
from boto.exception import S3ResponseError
import zipfile
import time
import StringIO
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from apps.canvas_auth.models import User
from canvas.models import UserInfo
from drawquest.apps.quests.models import Quest
from drawquest.apps.quest_comments.models import QuestComment
from drawquest.apps.following import models as following_models
from canvas.models import Comment

# Questbot = 319627

class S3(object):
    def __init__(self, bucket, prefix=""):
        conn = S3Connection(*aws)
        self.bucket = conn.get_bucket(bucket, validate=False)
        self.prefix = prefix
    def read(self, filename):
        key = Key(self.bucket)
        key.key = self.prefix + filename
        return key.get_contents_as_string()
    def read_to_fp(self, filename, fp):
        key = Key(self.bucket)
        key.key = self.prefix + filename
        return key.get_contents_to_file(fp)
    def copy_to_other_s3(self, filename, other_s3, to_filename):
        key = Key(self.bucket)
        key.key = self.prefix + filename
        key.copy(other_s3.bucket, to_filename)
    def save(self, filename, filedata, content_type='application/zip'):
        _, ext = os.path.splitext(filename)
        key = Key(self.bucket)
        key.key = self.prefix + filename
        key.set_contents_from_string(filedata, headers={'Content-Type': content_type}, policy='public-read')
    def list(self, dir_prefix):
        return self.bucket.list(dir_prefix)


skip_images = False


class Command(BaseCommand):
    args = ''
    help = ""

    def handle(self, from_id, to_id, worker_count, my_id, *args, **options):
        from_fs = S3('drawquest_public_ugc')
        to_fs = S3('drawquest-export')
        playback_from_fs = S3('drawquest-playbacks')

        last_id = None
        try:
            with open('worker_{}_of_{}'.format(my_id, worker_count), 'r') as worker_file:
                lines = worker_file.readlines()
                if lines and worker_count > 1:
                    last = lines[-1]
                    last_id = last.split(' ')[1]
        except IOError:
            pass

        # Deletes the file
        #open('worker_{}_of_{}'.format(my_id, worker_count), 'w').close()

        if int(my_id) == 0 or int(worker_count) == 1:
            home_html = r2r_jinja('exporter_home.html', {
            }).content
            to_fs.save('/index.html', home_html, content_type='text/html')
            users_html = r2r_jinja('exporter_users.html', {
                'usernames': User.objects.all().order_by('id').values_list('username', flat=True)
            }).content
            to_fs.save('/all_users.html', users_html, content_type='text/html')

        # old canvas values
        #id_start = 15262
        #id_end = 45000
        #id_start = 35218#85000
        #id_end = 45000

        class Drawing(object):
            def __init__(self, cid, url, star_count, visibility, playback_url, ts, parent_comment_id, author_id):
                self.id = cid
                self.url = url
                self.star_count = star_count
                self.visible = visibility != 2 # not disabled
                self.author_username = user_id_to_username[author_id]
                self.detail_url = '/{}/drawings/{}.html'.format(self.author_username, self.id)
                self.playback_url = playback_url
                self.date = datetime.datetime.fromtimestamp(ts).strftime('%b %-d, %Y')

                if parent_comment_id:
                    q = self.quest = all_quests[parent_comment_id]
                    self.quest_id = parent_comment_id
                    self.quest_title = q['title']
                    self.quest_author_username = user_id_to_username[q['author_id']]
                    if q['ugq']:
                        self.quest_detail_url = '/{}/quests/{}.html'.format(self.quest_author_username, self.quest_id)
                    else:
                        self.quest_detail_url = '/Questbot/quests/{}.html'.format(self.quest_id)
                    self.quest_image_url = None
                    if q['reply_content_id']:
                        if q['ugq']:
                            self.quest_image_url = '/{}/quests/{}.png'.format(self.quest_author_username, q['reply_content_id'])
                        else:
                            self.quest_image_url = '/Questbot/quests/quest_id_{}.png'.format(q['id'])

        class ArchivedQuest(object):
            def __init__(self, cid, url, visibility, ts, title, author_id):
                self.id = cid
                self.url = url
                self.date = datetime.datetime.fromtimestamp(ts).strftime('%b %d, %Y')
                self.title = title
                self.reply_count = Quest.all_objects.get(id=cid).replies.count()
                self.reply_count_f = '{:,d}'.format(self.reply_count)

                # FIXME questbot
                self.detail_url = '/{}/quests/{}.html'.format(user_id_to_username[author_id], self.id)

        #id_start = 0
        #id_end = 999999999999999#4
        id_start = int(from_id)
        id_end = int(to_id)

        if last_id is not None:
            id_start = last_id
            print 'Resuming from {}'.format(last_id)

        user_id_to_username = dict(User.objects.all().values_list('id', 'username'))

        all_quests = dict((q['id'], q) for q in Quest.all_objects.values('title', 'author_id', 'ugq', 'reply_content_id', 'id'))

        recopy_files = False

        for user2 in User.objects.filter(id__gte=id_start).exclude(id__gt=id_end).order_by('id').select_related('userinfo').iterator():
            if int(user2.id) % int(worker_count) != int(my_id):
                continue
            l = "id: %s username: %r email: %r" % (user2.id, user2.username, user2.email)
            with open('worker_{}_of_{}'.format(my_id, worker_count), 'a') as logf:
                logf.write(l + '\n')
            print l

            if user2.username == 'Questbot':
                comment_ids = [s.quest.id for s in ScheduledQuest.archived(select_quests=True)]
                comments = Comment.all_objects.filter(id__in=comment_ids).order_by('-id').values_list('id', 'reply_content_id', 'ugq', 'star_count', 'visibility', 'timestamp', 'parent_comment_id', 'title')
            else:
                comments = Comment.all_objects.filter(author=user2).order_by('-id').values_list('id', 'reply_content_id', 'ugq', 'star_count', 'visibility', 'timestamp', 'parent_comment_id', 'title')
            #
            #content_ids = [id_ for id_, _ in comments]
            #content_metadatas = ContentMetadata.objects.filter(content_id__in=content_ids)
            #
            num_ids = len(comments)
            last = time.time()
            n = 0
            total = 0
            skipped_existing = 0
            drawings = []
            quests = []
            quest_urls = []
            playback_urls = []
            all_last = time.time()
            if user2.username == 'soap':
                user2.username = 'Soap'
            user_dir = u'{}/'.format(user2.username)
            if not skip_images:
                existing_filenames = set(e.name for e in to_fs.list(user2.username))

            try:
                avatar = user2.userinfo.avatar
            except UserInfo.DoesNotExist:
                avatar = None
            avatar_url = None
            full_avatar_url = None
            if avatar:
                avatar_details = avatar.details()
                avatar_from_filename = avatar_details['gallery'].get('url')
                avatar_from_filename = avatar_from_filename.split('http://i.drawquestugc.com/ugc/')[-1]
                full_avatar_from_filename = avatar_details['original'].get('name')
                full_avatar_ext = full_avatar_from_filename.split('.')[-1]
                avatar_ext = avatar_from_filename.split('.')[-1]
                avatar_to_filename = user_dir + 'avatar.{}'.format(avatar_ext)
                full_avatar_to_filename = user_dir + 'avatar_fullsize.{}'.format(full_avatar_ext)
                try:
                    if not skip_images and (recopy_files or (avatar_to_filename not in existing_filenames)):
                        from_fs.copy_to_other_s3(avatar_from_filename, to_fs, avatar_to_filename)
                except S3ResponseError as e:
                    print e
                try:
                    if not skip_images and (recopy_files or (full_avatar_to_filename not in existing_filenames)):
                        from_fs.copy_to_other_s3(full_avatar_from_filename, to_fs, full_avatar_to_filename)
                except S3ResponseError as e:
                    print e
                avatar_url = ('http://drawquest-export.s3-website-us-east-1.amazonaws.com/'
                              + avatar_to_filename)
                full_avatar_url = ('http://drawquest-export.s3-website-us-east-1.amazonaws.com/'
                              + full_avatar_to_filename)

            for comment_id, content_id, is_ugq, star_count, visibility, timestamp, quest_id, title in comments: #[2:3]:
                def make_quest_page(quest):
                    top_replies = QuestComment.objects.filter(
                        parent_comment_id=quest.id).order_by('-star_count')
                    top_replies = top_replies.values('id', 'reply_content_id', 'star_count', 'visibility', 'timestamp', 'author_id')
                    top_replies = top_replies[:500]

                    top_reply_drawings = []
                    for tr in top_replies:
                        reply_to_filename = '{}/drawings/{}.png'.format(user_id_to_username[tr['author_id']], tr['reply_content_id'])
                        top_reply_drawings.append(Drawing(tr['id'], 'http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + reply_to_filename, tr['star_count'], tr['visibility'], None, tr['timestamp'], None, tr['author_id']))

                    quest_html = r2r_jinja('exporter_quest.html', {
                        'user': user2, 'q': quest,
                        'avatar_url': avatar_url,
                        'top_replies': top_reply_drawings,
                    }).content
                    to_fs.save(user_dir + 'quests/{}.html'.format(quest.id), quest_html, content_type='text/html')

                if is_ugq and content_id is None:
                    quest = ArchivedQuest(comment_id, None, visibility, timestamp, title, user2.id)
                    quests.append(quest)
                    make_quest_page(quest)
                    continue

                filename = 'original/{}.png'.format(content_id)
                #details_id = ('content:' + id_ + ':details').encode('ascii')
                #raw = redis.get(details_id)
                #if not raw:
                #    continue
                #details = util.loads(raw)
                #try:
                #    filename = details['original']['name']
                #except KeyError:
                #    print "KeyError: ",
                #    print details
                #    continue
                drawing_filename = filename.split('original/')[-1]

                if is_ugq or user2.username == 'Questot':
                    to_filename = user_dir + 'quests/' + drawing_filename
                else:
                    to_filename = user_dir + 'drawings/' + drawing_filename

                try:
                    if not skip_images and (recopy_files or (to_filename not in existing_filenames)):
                        from_fs.copy_to_other_s3(filename, to_fs, to_filename)
                    else:
                        skipped_existing += 1
                except S3ResponseError:
                    continue

                playback_url = None
                if user2.username != 'Questbot':
                    playback_to_filename = user_dir + 'playback_data/' + content_id + '.json.gz'

                    try:
                        if not skip_images and (recopy_files or (playback_to_filename not in existing_filenames)):
                            playback_from_fs.copy_to_other_s3('{}-{}.json.gz'.format(content_id, comment_id), to_fs, playback_to_filename)
                        else:
                            pass #skipped_existing += 1
                        playback_url = 'http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + playback_to_filename
                        playback_urls.append(playback_url)
                    except S3ResponseError:
                        pass

                if is_ugq or user2.username == 'Questbot':
                    quest = ArchivedQuest(comment_id, 'http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + to_filename, visibility, timestamp, title, user2.id)
                    quests.append(quest)
                    make_quest_page(quest)
                else:
                    drawing = Drawing(comment_id, 'http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + to_filename, star_count, visibility, playback_url, timestamp, quest_id, user2.id)
                    drawings.append(drawing)

                    # Playback page.
                    playback_html = r2r_jinja('exporter_playback.html', {
                        'user': user2, 'd': drawing, 'playback_url': playback_url,
                        'avatar_url': avatar_url,
                    }).content
                    to_fs.save(user_dir + 'drawings/{}.html'.format(drawing.id), playback_html, content_type='text/html')

                total += time.time() - last
                n += 1.
                last = time.time()

            follow_counts = following_models.counts(user2)
            follower_ids = user2.redis.new_followers.zrange(0, -1)
            following_ids = user2.redis.new_following.zrange(0, -1)
            follower_usernames = sorted([v for k,v in user_id_to_username.iteritems() if str(k) in follower_ids], key=lambda e: e.lower())
            following_usernames = sorted([v for k,v in user_id_to_username.iteritems() if str(k) in following_ids], key=lambda e: e.lower())

            if user2.username != 'Questbot':
                quests = sorted(quests, key=lambda q: -q.reply_count)

            index_html = r2r_jinja('exporter_index.html', {
                'user': user2, 'quests': quests, 'drawings': drawings, 'playback_urls': playback_urls,
                'follower_count': follow_counts['followers'],
                'follower_count_f': '{:,d}'.format(follow_counts['followers']),
                'quest_count': len(quests),
                'following_count': follow_counts['following'],
                'following_count_f': '{:,d}'.format(follow_counts['following']),
                'follower_usernames': follower_usernames,
                'drawing_count': len(drawings),
                'following_usernames': following_usernames,
                'avatar_url': avatar_url,
                'full_avatar_url': full_avatar_url,
                'date_joined': user2.date_joined.strftime('%b %-d, %Y'),
            }).content
            to_fs.save(user_dir + 'index.html', index_html, content_type='text/html')
            print (u"finished {} images ({} skipped) for user {} in {}s".format(num_ids, skipped_existing, user2.username, time.time() - all_last)).encode('utf8')


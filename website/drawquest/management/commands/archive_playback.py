from configuration import aws
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
from drawquest.apps.following import models as following_models
from canvas.models import Comment

class S3(object):
    def __init__(self, bucket, prefix=""):
        conn = S3Connection(*aws)
        self.bucket = conn.get_bucket(bucket)
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


class Command(BaseCommand):
    args = ''
    help = ""

    def handle(self, from_id, to_id, worker_count, my_id, *args, **options):
        to_fs = S3('drawquest-export')

        class Drawing(object):
            def __init__(self, cid, url, star_count, visibility):
                self.id = cid
                self.url = url
                self.star_count = star_count
                self.visible = visibility != 2 # not disabled

        id_start = 0
        id_end = 999999999999999#4

        for user2 in User.objects.filter(id__gte=id_start).exclude(id__gt=id_end).order_by('id').select_related('userinfo').iterator():
            if int(user2.id) % int(worker_count) != int(my_id):
                continue
        #for user2 in User.objects.filter(id__in=list(Comment.objects.order_by('-id').values_list('author_id', flat=True).distinct()[:50])).iterator():
            #user = User.objects.get(username='photocopier')
            print "id: %s username: %r email: %r" % (user2.id, user2.username, user2.email)
            #
            comments = Comment.all_objects.filter(author=user2).exclude(reply_content__isnull=True).values_list('id', 'reply_content_id', 'ugq', 'star_count', 'visibility')
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
            quest_urls = []
            playback_urls = []
            all_last = time.time()
            user_dir = u'{}/'.format(user2.username)
            existing_filenames = [e.name for e in to_fs.list(user2.username)]
            #
            for comment_id, content_id, is_ugq, star_count, visibility in comments: #[2:3]:
                filename = 'original/{}.png'.format(content_id)
                drawing_filename = filename.lstrip('original/')

                if is_ugq:
                    to_filename = user_dir + 'quests/' + drawing_filename
                else:
                    to_filename = user_dir + 'drawings/' + drawing_filename

                try:
                    if recopy_files or (to_filename not in existing_filenames):
                        from_fs.copy_to_other_s3(filename, to_fs, to_filename)
                    else:
                        skipped_existing += 1
                except S3ResponseError:
                    continue

                playback_to_filename = user_dir + 'playback_data/' + content_id + '.json.gz'

                try:
                    if recopy_files or (playback_to_filename not in existing_filenames):
                        playback_from_fs.copy_to_other_s3('{}-{}.json.gz'.format(content_id, comment_id), to_fs, playback_to_filename)
                    else:
                        skipped_existing += 1
                    playback_urls.append('http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + playback_to_filename)
                except S3ResponseError:
                    continue

                if is_ugq:
                    quest_urls.append('http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + to_filename)
                else:
                    drawings.append(Drawing(comment_id, 'http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + to_filename, star_count, visibility))

                total += time.time() - last
                n += 1.
                last = time.time()

            follow_counts = following_models.counts(user2)
            follower_ids = user2.redis.new_followers.zrange(0, -1)
            following_ids = user2.redis.new_following.zrange(0, -1)
            follower_usernames = [v for k,v in user_id_to_username.iteritems() if str(k) in follower_ids]
            following_usernames = [v for k,v in user_id_to_username.iteritems() if str(k) in following_ids]
            #
            avatar = user2.userinfo.avatar
            avatar_url = None
            if avatar:
                avatar_details = avatar.details()
                avatar_from_filename = avatar_details['gallery'].get('url')
                avatar_ext = avatar_from_filename.split('.')[-1]
                avatar_to_filename = user_dir + 'avatar.{}'.format(avatar_ext)
                try:
                    if recopy_files or (avatar_to_filename not in existing_filenames):
                        from_fs.copy_to_other_s3(avatar_from_filename, to_fs, avatar_to_filename)
                    playback_urls.append('http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + playback_to_filename)
                except S3ResponseError:
                    continue
                avatar_url = ('http://drawquest-export.s3-website-us-east-1.amazonaws.com/'
                              + avatar_to_filename)
            #
            index_html = r2r_jinja('exporter_index.html', {
                'user': user2, 'quest_urls': quest_urls, 'drawings': drawings, 'playback_urls': playback_urls,
                'follower_count': follow_counts['followers'],
                'following_count': follow_counts['following'],
                'follower_usernames': follower_usernames,
                'following_usernames': following_usernames,
                'avatar_url': avatar_url,
            })
            index_html = index_html.content
            to_fs.save(user_dir + 'index.html', index_html, content_type='text/html')
            print u"finished {} images ({} skipped) for user {} in {}s".format(num_ids, skipped_existing, user2.username, time.time() - all_last)



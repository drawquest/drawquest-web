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
from canvas.models import UserInfo
from drawquest.apps.following import models as following_models
from canvas.models import Comment
from drawquest.apps.quests.models import Quest


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


class Command(BaseCommand):
    args = ''
    help = ""

    def handle(self, *args, **options):
        from_fs = S3('drawquest_public_ugc')
        to_fs = S3('drawquest-export')

        class Drawing(object):
            def __init__(self, cid, url, star_count, visibility):
                self.id = cid
                self.url = url
                self.star_count = star_count
                self.visible = visibility != 2 # not disabled

        id_start = 0
        id_end = 4#999999999999999

        recopy_files = False

        quests = Quest.objects.filter(ugq=False)

        num_ids = quests.count()
        last = time.time()
        n = 0
        skipped_existing = 0
        all_last = time.time()
        quest_urls = []
        existing_filenames = set(e.name for e in to_fs.list('Questbot'))

        for quest in quests.iterator():
            l = "id: %s title: %s" % (quest.id, quest.title)
            print l

            filename = 'original/{}.png'.format(quest.reply_content_id)
            drawing_filename = filename.split('original/')[-1]

            to_filename = 'Questbot/quests/' + drawing_filename
            try:
                if recopy_files or (to_filename not in existing_filenames):
                    from_fs.copy_to_other_s3(filename, to_fs, to_filename)
                else:
                    skipped_existing += 1
            except S3ResponseError:
                continue

            to_filename2 = 'Questbot/quests/quest_id_{}.png'.format(quest.id)
            try:
                if recopy_files or (to_filename2 not in existing_filenames):
                    from_fs.copy_to_other_s3(filename, to_fs, to_filename2)
            except S3ResponseError:
                continue

            quest_urls.append('http://drawquest-export.s3-website-us-east-1.amazonaws.com/' + to_filename)

            n += 1.
            last = time.time()

            #index_html = r2r_jinja('exporter_index.html', {
            #    'user': user2, 'quest_urls': quest_urls, 'drawings': drawings, 'playback_urls': playback_urls,
            #    'follower_count': follow_counts['followers'],
            #    'following_count': follow_counts['following'],
            #    'follower_usernames': follower_usernames,
            #    'following_usernames': following_usernames,
            #    'avatar_url': avatar_url,
            #    'full_avatar_url': full_avatar_url,
            #})
            #index_html = index_html.content
            #to_fs.save(user_dir + 'index.html', index_html, content_type='text/html')
            print u"finished {} quest images ({} skipped) for Questbot in {}s".format(num_ids, skipped_existing, time.time() - all_last)



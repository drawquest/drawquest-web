from uuid import UUID
import gzip
from ssl import SSLError
import StringIO

from boto.exception import S3ResponseError
from django.db.models import *
from django.db import IntegrityError
from simplejson import JSONDecodeError

from canvas import json, bgwork
from canvas.models import BaseCanvasModel
from canvas.notifications.actions import Actions
from canvas.storage import get_fs
from canvas.util import UnixTimestampField, Now
from drawquest.apps.drawquest_auth.models import User
from drawquest.apps.quest_comments.models import QuestComment


class Playback(BaseCanvasModel):
    comment = ForeignKey(QuestComment, related_name='playbacks', null=False)
    viewer = ForeignKey(User, null=False)
    timestamp = UnixTimestampField(default=0)

    class Meta(object):
        unique_together = ('comment', 'viewer',)

    @classmethod
    def append(cls, **kwargs):
        """ Ignores dupes. """
        if not 'timestamp' in kwargs:
            kwargs['timestamp'] = Now()

        instance = cls(**kwargs)

        try:
            instance.save()
        except IntegrityError:
            return

        instance.comment.details.force()

        @bgwork.defer
        def playback_action():
            Actions.playback(instance.viewer, instance.comment)

    def to_client(self, **kwargs):
        return {
            'timestamp': self.timestamp,
            'viewer': self.viewer,
        }

def get_playback_data(comment):
    try:
        fs = get_fs(*settings.PLAYBACK_FS)
    except SSLError:
        return None

    def read_file(filename):
        gzipped_data = fs.read(filename)
        f = gzip.GzipFile(fileobj=StringIO.StringIO(gzipped_data))
        data = f.read()
        f.close()
        return data

    try:
        data = read_file(comment.playback_filename)
    except (S3ResponseError, IOError):
        try:
            data = read_file(filename_for_uuid(comment.uuid))
        except (S3ResponseError, IOError, ValueError):
            data = None

    return data

def save_stroke_count(comment, playback_data):
    stroke_count = None

    if isinstance(playback_data, basestring):
        try:
            playback_data = json.loads(playback_data)
        except JSONDecodeError:
            stroke_count = playback_data.count('components')

    if stroke_count is None:
        try:
            stroke_count = len(playback_data['strokes'])
        except (KeyError, TypeError,):
            return

    comment.reply_content.stroke_count = stroke_count
    comment.reply_content.save()

def uuid_string_to_int(uuid):
    uuid = UUID(uuid)
    return uuid.int

def filename_for_uuid(uuid):
    if uuid is None:
        raise ValueError('UUID must not be None')

    if isinstance(uuid, basestring):
        uuid = uuid_string_to_int(uuid)

    return '{}-uuid.json.gz'.format(uuid)

def save_playback_data(playback_data, comment=None, uuid=None):
    if comment is None and uuid is None:
        raise ValueError("Must supply either a comment or a UUID.")

    if uuid is not None:
        try:
            comment = QuestComment.objects.get(uuid=uuid_string_to_int(uuid))
        except QuestComment.DoesNotExist:
            filename = filename_for_uuid(uuid)

    if comment is not None:
        filename = comment.playback_filename

    gzipped = StringIO.StringIO()
    f = gzip.GzipFile(fileobj=gzipped, mode='w')
    f.write(playback_data)
    f.close()

    try:
        fs = get_fs(*settings.PLAYBACK_FS)
    except SSLError:
        return None

    if fs is not None:
        fs.save(comment.playback_filename, gzipped.getvalue())

    if comment is not None:
        save_stroke_count(comment, playback_data)


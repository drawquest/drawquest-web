import os
from ssl import SSLError

from boto.s3.connection import S3Connection
from boto.s3.key import Key

from compressor.storage import CompressorFileStorage
from configuration import aws


def get_fs(fs_type, *args):
    def _get_fs(*args):
        fs_lookup = {
            'local': LocalDiskFS,
            's3': SimpleStorageServiceFS,
        }
        return fs_lookup[fs_type](*args)

    fs = None
    tries = 4
    for try_ in range(1, tries + 1):
        try:
            fs = _get_fs(*args)
            break
        except SSLError as e:
            if try_ == tries:
                raise e

    return fs


class CanvasFileStorage(CompressorFileStorage):
    def url(self, path):
        return "//canvas-dynamic-assets.s3.amazonaws.com/static/" + path


class LocalDiskFS(object):
    def __init__(self, root):
        self.root = root

    def save(self, filename, filedata):
        filepath = os.path.join(self.root, filename)
        output = file(filepath, 'wb')
        try:
            output.write(filedata)
        finally:
            output.close()

        os.chmod(filepath, 0644) # Intentionally octal, world readable for nginx

    def read(self, filename):
        filepath = os.path.join(self.root, filename)
        return file(filepath, 'rb').read()


class SimpleStorageServiceFS(object):
    def __init__(self, bucket, prefix=""):
        conn = S3Connection(*aws)
        self.bucket = conn.get_bucket(bucket)
        self.prefix = prefix

    def read(self, filename):
        key = Key(self.bucket)
        key.key = self.prefix + filename
        return key.get_contents_as_string()

    def save(self, filename, filedata):
        _, ext = os.path.splitext(filename)
        content_type = ({
            '.gif': 'image/gif',
            '.png': 'image/png',
            '.json': 'application/json',
            '.gz': 'application/x-gzip',
        }).get(ext.lower(), 'image/jpeg')

        key = Key(self.bucket)
        key.key = self.prefix + filename
        key.set_contents_from_string(filedata, headers={'Content-Type': content_type})


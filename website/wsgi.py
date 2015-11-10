import cStringIO
import logging
import os
import zlib

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")

# This application object is used by the development server
# as well as any WSGI server configured to use this file.
from django.core.wsgi import get_wsgi_application

logger = logging.getLogger(__name__)

# https://groups.google.com/forum/#!topic/modwsgi/VOuo3f8ajuw
class GunzipRequestsWrapper(object):
    def __init__(self, application):
        self.__application = application

    def __call__(self, environ, start_response):
        if environ.get('HTTP_CONTENT_ENCODING', '') == 'gzip':
            buffer = cStringIO.StringIO()
            input = environ['wsgi.input']
            blksize = 2**13
            length = 0

            decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

            data = input.read(blksize)
            decompressed_data = decompressor.decompress(data)
            buffer.write(decompressed_data)
            length += len(decompressed_data)

            while data:
                data = input.read(blksize)
                decompressed_data = decompressor.decompress(data)
                buffer.write(decompressed_data)
                length += len(decompressed_data)

            v = buffer.getvalue()
            buffer = cStringIO.StringIO(v)

            environ['wsgi.input'] = buffer
            environ['CONTENT_LENGTH'] = length

        return self.__application(environ, start_response)


application = GunzipRequestsWrapper(get_wsgi_application())


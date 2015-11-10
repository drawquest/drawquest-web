from cStringIO import StringIO
from hashlib import sha1
import math
import os
from time import time

from PIL import Image
from django.conf import settings
from django.db import IntegrityError
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, returnValue

from canvas import util
from canvas.models import Content, Comment, ContentUrlMapping, Visibility
from canvas.redis_models import redis
from configuration import Config

# Workaround jpeg quality saving issues:
# http://mail.python.org/pipermail/image-sig/1999-August/000816.html
from PIL import ImageFile
ImageFile.MAXBLOCK = 4 * 1024 * 10214 # default is 64k


EXTENSION_FROM_FORMAT = {
    'JPEG': '.jpg',
    'GIF': '.gif',
    'PNG': '.png',
    'BMP': '.bmp',
}

hexdigest = lambda data: sha1(data).hexdigest()

def count_frames(img):
    frames = 1

    if img.format == 'GIF':
        try:
            while True:
                img.seek(img.tell() + 1)
        except EOFError:
            frames = img.tell()
        finally:
            img.seek(0)

    return frames

def generate_thumbnails(image_file_data, fs=None, image_type=None, filename=None, exclude_types=[]):
    """
    Specify an `image_type` to recreate just one image type.

    Returns a metadata object.
    """
    if fs is None:
        from canvas.upload import get_fs
        fs = get_fs(*settings.IMAGE_FS)

    thumbnailer = Thumbnailer(fs)
    return thumbnailer.store(image_file_data, image_type=image_type, filename=filename, exclude_types=exclude_types)

def create_content(ip, fs, data, remix_of, stamps_used, is_quest=False):
    from drawquest.apps.content_metadata.models import save_content_metadata_from_legacy_dict

    util.papertrail.debug('UPLOADS: create_content, is_quest={}'.format(is_quest))

    exclude_types = []

    if not is_quest:
        exclude_types = ['homepage_featured']

    meta = generate_thumbnails(data, fs=fs, exclude_types=exclude_types)
    util.papertrail.debug('UPLOADS: thumbnails generated for ID {}'.format(meta['id']))

    if remix_of:
        remix_of = Content.all_objects.get(id=remix_of)
        remix_of.hide_if_unpublished()
    else:
        remix_of = None

    if stamps_used:
        stamps_used = [Content.all_objects.get_or_none(id=stamp_id) for stamp_id in stamps_used if stamp_id]
        stamps_used = [stamp for stamp in stamps_used if stamp]

    try:
        util.papertrail.debug('UPLOADS: trying to get existing content with ID {}'.format(meta['id']))
        content = Content.all_objects.get(id=meta['id'])
        util.papertrail.debug('UPLOADS: got existing content for ID {}'.format(meta['id']))
        # Don't allow uploading content that has been disabled.
        if content.visibility == Visibility.DISABLED:
            return {
                'success': False,
                'reason': 'This image has been banned.',
            }
    except Content.DoesNotExist:
        util.papertrail.debug('UPLOADS: creating content with ID {}'.format(meta['id']))
        content = Content(
            id = meta['id'],
            visibility = Visibility.UNPUBLISHED,
            ip = ip,
            timestamp = time(),
            remix_of = remix_of,
        )
        util.papertrail.debug('UPLOADS: instantiated content with ID {}'.format(meta['id']))

        try:
            content.save(force_insert=True)
            util.papertrail.debug('UPLOADS: saved content with ID {}'.format(meta['id']))
            util.papertrail.debug('UPLOADS: saved content with ID {}, has pk {}'.format(meta['id'], content.pk))
            util.papertrail.debug('UPLOADS: actual content object for ID {} exists: {}'.format(meta['id'], Content.all_objects.filter(id=meta['id']).exists()))
            util.papertrail.debug('UPLOADS: actual content object for ID {} exists using pk: {}'.format(meta['id'], Content.all_objects.filter(id=content.pk).exists()))
            util.papertrail.debug('UPLOADS: actual content object for ID {} exists using pk2: {}'.format(meta['id'], Content.all_objects.filter(pk=content.pk).exists()))
        except IntegrityError:
            util.papertrail.debug('UPLOADS: integrity error when trying to create content with ID {}'.format(meta['id']))
            # Race condition, retry
            return create_content(ip, fs, data, remix_of, stamps_used, is_quest=is_quest)

        content.stamps_used.add(*stamps_used)

        util.papertrail.debug('UPLOADS: creating metadata for ID {}'.format(meta['id']))
        save_content_metadata_from_legacy_dict(content, meta)
        util.papertrail.debug('UPLOADS: created metadata for ID {}'.format(meta['id']))

    util.papertrail.debug('UPLOADS: returning metadata for ID {}'.format(meta['id']))
    return {'success': True, 'content': content.details.force()}

def update_all_content(fs, resume_percent=0.0, stop_percent=1.0, image_type=None):
    total = Content.all_objects.all().count()

    start_slice = math.floor(float(resume_percent) * total)
    stop_slice = math.ceil(float(stop_percent) * total)
    if image_type is None:
        print "Rethumbnailing images %s-%s of %s" % (start_slice, stop_slice, total)
    else:
        print "Rethumbnailing images of type %s, %s-%s of %s" % (image_type, start_slice, stop_slice, total)
    contents = Content.all_objects.all()
    for i, content in enumerate(contents[start_slice:stop_slice]):
        print "%05.2f%% complete. Updating: %s" % ((i+start_slice) * 100.0 / total, content.id)
        try:
            update(fs, content, image_type=image_type, save_to_db=False)
        except Exception:
            import traceback
            traceback.print_exc()
            print "ERROR: Something is wrong with content: %s" % content.details()

def update(fs, content, image_type, save_to_db=True):
    from drawquest.apps.content_metadata.models import save_content_metadata_from_legacy_dict

    filename = content.details()['original']['name']
    # Prevent issues with unicode filenames.
    filename = filename.encode('ascii')
    data = fs.read(filename)

    thumbnailer = Thumbnailer(fs)

    meta = util.loads(redis.get(content.details_key))
    meta.update(thumbnailer.store(data, image_type))

    if save_to_db:
        content.save()

    save_content_metadata_from_legacy_dict(content, meta)

    content.details.force()

def image_entropy(img):
    histogram = img.histogram()
    histogram_length = sum(histogram)
    samples_probability = [float(h) / histogram_length for h in histogram]
    return -sum([p * math.log(p, 2) for p in samples_probability if p != 0])

def thumbnail(img, x, y, crop_y=False, crop_x=False, intelligent_crop=False, filter_=Image.ANTIALIAS):
    # Slightly prefer the top of images when cropping, if the bottom isn't much more interesting.
    top_entropy_bias = 1.25

    if img.mode == 'RGBA' or (img.mode == 'P' and 'transparency' in img.info):
        convert_to = 'RGBA'
    else:
        convert_to = 'RGB'

    thumb = img.convert(convert_to)

    ix, iy = thumb.size
    if crop_y and crop_x:
        if ix > iy:
            crop_y = None
        else:
            crop_x = None

    cy, cx = 0, 0

    if not crop_y and not crop_x:
        thumb.thumbnail((x,y), filter_)

    elif crop_y and not crop_x:
        target_aspect = float(y)/x
        aspect = float(iy)/ix

        # Rescale horizontally if necessary.
        fx, fy = float(x), float(y)
        if ix > fx:
            scale = fx / ix
            new_size = [int(math.ceil(v)) for v in [(ix * scale), (iy * scale)]]
            thumb = thumb.resize(new_size, filter_)
            ix, iy = thumb.size

        # Crop vertically.
        if intelligent_crop:
            while (iy - cy) > y:
                # Slice until we're at the target size
                slice_height = min((iy - cy) - y, 8)
                top = thumb.crop((0, cy, ix, cy + slice_height))
                bottom = thumb.crop((0, iy - slice_height, ix, iy))

                if image_entropy(top) * top_entropy_bias > image_entropy(bottom):
                    iy -= slice_height
                else:
                    cy += slice_height
        else:
            if iy > y:
                strip = (iy - y) / 2.0
                iy -= int(math.ceil(strip))
                cy = int(math.floor(strip))

        thumb = thumb.crop((cx, cy, ix, iy))

    elif crop_x and not crop_y:
        target_aspect = float(y)/x
        aspect = float(iy)/ix

        # Rescale vertically if necessary.
        fx, fy = float(x), float(y)
        if iy > fy:
            scale = fy / iy
            new_size = [int(math.ceil(v)) for v in [(ix * scale), (iy * scale)]]
            thumb = thumb.resize(new_size, filter_)
            ix, iy = thumb.size

        # Crop horizontally.
        if intelligent_crop:
            while (ix - cx) > x:
                # Slice until we're at the target size
                slice_width = min((ix - cx) - x, 8)
                left = thumb.crop((cx, 0, cx + slice_width, iy))
                right = thumb.crop((ix - slice_width, 0, ix, iy))

                if image_entropy(left) * top_entropy_bias > image_entropy(right):
                    ix -= slice_width
                else:
                    cx += slice_width
        else:
            if ix > x:
                strip = (ix - x) / 2.0
                ix -= int(math.ceil(strip))
                cx = int(math.floor(strip))

        thumb = thumb.crop((cx, cy, ix, iy))

    return thumb

def determine_alpha(img):
    """ Insanely brittle, because this stuff seems really untested in PIL :( """
    img.load()

    if 'P' in img.getbands():
        img = img.convert('RGBA')
        img.load()

    bands = dict(zip(img.getbands(), img.getextrema()))

    amin, amax = bands.get('A', [255,255])
    return amin < 0xFF


class Thumbnailer(object):
    # large explore thumb: 860x645
    # small explore thumb: 373x280
    META = {
        'id': lambda self, img, data, **kwargs: hexdigest(data),
        'original': lambda self, img, data, **kwargs: self.store_image(img, filedata=data),
        'gallery': lambda self, img, data, **kwargs: self.store_image(thumbnail(img, 1212,908, crop_y=True), format_='JPEG'),
        'homepage_featured': lambda self, img, data, **kwargs: self.store_image(thumbnail(img, 783,588, crop_y=True), format_='JPEG'),
        'archive': lambda self, img, data, **kwargs: self.store_image(thumbnail(img, 277,207, crop_y=True), format_='JPEG'),
        'activity': lambda self, img, data, **kwargs: self.store_image(thumbnail(img, 114,85, crop_y=True, filter_=Image.BICUBIC), format_='JPEG'),
        'iphone_gallery': lambda self, img, data, **kwargs: self.store_image(thumbnail(img, 604,452, crop_y=True, filter_=Image.BICUBIC), format_='JPEG'),
    }

#604, 452

    CLONED_META = {
        'editor_template': 'original',
        'camera_roll': 'original',
    }

    MANUAL_META = {}

    def __init__(self, fs):
        """
        fs:
            A "filesystem". See realtime.server.get_local_fs(), or look at test_thumbnailer.py
        """
        self.fs = fs

    def store(self, data, image_type=None, filename=None, exclude_types=[]):
        """ Saves a plethora of different versions of the image. See META. """
        if filename is not None and image_type is None:
            raise ValueError("Cannot specify a filename without also specifying a single image_type")

        img = Image.open(StringIO(data))

        if img.format not in EXTENSION_FROM_FORMAT:
            raise IOError("Unknown format type")

        meta = {}
        # Rethumbnail everything, or just the specified type, and alpha if we rethumbnailed 'original'.
        calculate_alpha = True
        if image_type is None:
            for _image_type, fn in self.META.items():
                if _image_type in exclude_types:
                    continue

                meta[_image_type] = fn(self, img, data, filename=filename)

            for _clone_type, _image_type in self.CLONED_META.items():
                if _clone_type in exclude_types:
                    raise Exception("Can't exclude a cloned thumbnail type.")

                meta[_clone_type] = meta[_image_type]
        else:
            if image_type in self.CLONED_META:
                raise Exception("Regenerate {} instead, since this is just a cloned thumbnail.".format(self.CLONED_META[image_type]))
            elif image_type in exclude_types:
                raise Exception("Can't exclude a type that you're explicitly generating.")

            fn = self.META.get(image_type, self.MANUAL_META[image_type])
            meta[image_type] = fn(self, img, data, filename=filename)
            calculate_alpha = image_type == 'original'

            for _clone_type, _image_type in self.CLONED_META.items():
                if _image_type == image_type:
                    meta[_clone_type] = meta[image_type]

        if calculate_alpha:
            # This must go last, because PIL doesn't know how to non-destructively get extrema (giant fucking bug
            # in PIL)
            meta['alpha'] = determine_alpha(img)

        return meta

    def store_image(self, img, filedata=None, filename=None, format_=None, quality=90):
        if format_ is None:
            format_ = img.format or ('JPEG' if img.mode == 'RGB' else 'PNG')

        original = bool(filedata)
        if not filedata:
            imgio = StringIO()
            if format_ == 'JPEG':
                if img.mode == 'RGBA':
                    white_background = Image.new('RGB', img.size, (255,255,255))
                    white_background.paste(img, None, img)
                    img = white_background

                try:
                    img.save(imgio, format_, quality=quality, optimize=True)
                except IOError:
                    # http://stackoverflow.com/questions/6788398/how-to-save-progressive-jpeg-using-python-pil-1-1-7
                    old_max_block = ImageFile.MAXBLOCK
                    ImageFile.MAXBLOCK = max(img.size) ** 2
                    try:
                        img.save(imgio, format_, quality=quality, optimize=True)
                    finally:
                        ImageFile.MAXBLOCK = old_max_block
            else:
                img.save(imgio, format_)
            filedata = imgio.getvalue()

        if filename is not None:
            raise Exception("ContentMetadata needs to be updated to support custom filenames if we want to start using footers again.")

        id_ = hexdigest(filedata)
        filename = os.path.join('original' if original else 'processed',
                                id_ + EXTENSION_FROM_FORMAT[format_])
        self.fs.save(filename, filedata)

        data = {
            'name': filename,
            'width': img.size[0],
            'height': img.size[1],
            'id': id_,
        }

        if count_frames(img) > 1:
            data['animated'] = True

        return data


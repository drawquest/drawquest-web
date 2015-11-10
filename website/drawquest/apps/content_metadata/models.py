from django.db import models, transaction
from raven.contrib.django.raven_compat.models import client

from canvas.models import BaseCanvasModel, Content


@transaction.atomic
def save_content_metadata_from_legacy_dict(content, meta):
    metadata_kwargs = {}

    for key, val in meta.items():
        if key not in ['gallery', 'homepage_featured', 'archive', 'activity', 'iphone_gallery']:
            continue
        
        metadata_kwargs['{}_id'.format(key)] = val['id']

    try:
        metadata = ContentMetadata.objects.get(content_id=content.id)
    except ContentMetadata.MultipleObjectsReturned as e:
        metadata = ContentMetadata.objects.filter(content_id=content.id)[0]
        client.captureException()
    except (ContentMetadata.DoesNotExist, IndexError):
        metadata = ContentMetadata.objects.create(
            content_id = content.id,
            original_id = meta['id'],
            **metadata_kwargs)


class ContentMetadata(BaseCanvasModel):
    content_id = models.CharField(max_length=40, db_index=True)
    original_id = models.CharField(max_length=40) #TODO This is redundant, remove it.

    gallery_id = models.CharField(max_length=40)
    homepage_featured_id = models.CharField(max_length=40, blank=True)
    archive_id = models.CharField(max_length=40)
    activity_id = models.CharField(max_length=40)
    iphone_gallery_id = models.CharField(max_length=40, blank=True)

    @property
    def editor_template_id(self):
        return self.original_id

    @property
    def camera_roll_id(self):
        return self.original_id

    def to_client(self, viewer=None):
        ret = {'original': {'name': 'original/{}.png'.format(self.original_id)}}

        thumbs = [
            ('gallery', 'jpg', 'processed'),
            ('iphone_gallery', 'jpg', 'processed'),
            ('homepage_featured', 'jpg', 'processed'), 
            ('archive', 'jpg', 'processed'),
            ('activity', 'jpg', 'processed'),
            ('editor_template', 'png', 'original'),
            ('camera_roll', 'png', 'original'),
        ]

        for thumb, extension, folder in thumbs:
            id_ = getattr(self, '{}_id'.format(thumb))

            if id_:
                ret[thumb] = {'url': '{}/{}.{}'.format(folder, id_, extension)}

        return ret


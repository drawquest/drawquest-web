from django.conf import settings

from canvas.details_models import ContentDetails as CanvasContentDetails


class ContentDetails(CanvasContentDetails):
    UGC_IMAGES = [
        ('gallery', True),
        ('homepage_featured', True),
        ('archive', True),
        ('activity', True),
        ('editor_template', True),
    ]

    TO_CLIENT_WHITELIST = [
        'id',
        'timestamp',
        'original',
        'camera_roll',
        'iphone_gallery',
    ] + UGC_IMAGES

    def ugc_content(self, content):
        if content:
            try:
                url = content['url']
            except KeyError:
                url = content['name']

            return {'url': self.ugc_url(url)}

        return {}

    @property
    def camera_roll(self):
        return getattr(self, 'editor_template', None)

    @property
    def iphone_gallery(self):
        url = self._d.get('iphone_gallery', {}).get('url')
        
        if url is None:
            return getattr(self, 'gallery', None)
        
        return {'url': self.ugc_url(url)}

    @iphone_gallery.setter
    def iphone_gallery(self, val):
        self._d['iphone_gallery'] = val


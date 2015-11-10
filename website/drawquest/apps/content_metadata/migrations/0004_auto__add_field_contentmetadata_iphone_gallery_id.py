# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ContentMetadata.iphone_gallery_id'
        db.add_column(u'content_metadata_contentmetadata', 'iphone_gallery_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=40, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'ContentMetadata.iphone_gallery_id'
        db.delete_column(u'content_metadata_contentmetadata', 'iphone_gallery_id')


    models = {
        u'content_metadata.contentmetadata': {
            'Meta': {'object_name': 'ContentMetadata'},
            'activity_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'archive_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'content_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'gallery_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'homepage_featured_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'iphone_gallery_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'original_id': ('django.db.models.fields.CharField', [], {'max_length': '40'})
        }
    }

    complete_apps = ['content_metadata']
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'ContentMetadata', fields ['content_id']
        db.delete_unique(u'content_metadata_contentmetadata', ['content_id'])


        # Changing field 'ContentMetadata.content_id'
        db.alter_column(u'content_metadata_contentmetadata', 'content_id', self.gf('django.db.models.fields.CharField')(max_length=40))

    def backwards(self, orm):

        # Changing field 'ContentMetadata.content_id'
        db.alter_column(u'content_metadata_contentmetadata', 'content_id', self.gf('django.db.models.fields.BigIntegerField')(unique=True))
        # Adding unique constraint on 'ContentMetadata', fields ['content_id']
        db.create_unique(u'content_metadata_contentmetadata', ['content_id'])


    models = {
        u'content_metadata.contentmetadata': {
            'Meta': {'object_name': 'ContentMetadata'},
            'activity_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'archive_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'content_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'db_index': 'True'}),
            'gallery_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'homepage_featured_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_id': ('django.db.models.fields.CharField', [], {'max_length': '40'})
        }
    }

    complete_apps = ['content_metadata']
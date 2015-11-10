# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'ContentMetadata.original_id'
        db.add_column(u'content_metadata_contentmetadata', 'original_id',
                      self.gf('django.db.models.fields.CharField')(default='...', max_length=40),
                      keep_default=False)

        # Adding field 'ContentMetadata.gallery_id'
        db.add_column(u'content_metadata_contentmetadata', 'gallery_id',
                      self.gf('django.db.models.fields.CharField')(default='...', max_length=40),
                      keep_default=False)

        # Adding field 'ContentMetadata.homepage_featured_id'
        db.add_column(u'content_metadata_contentmetadata', 'homepage_featured_id',
                      self.gf('django.db.models.fields.CharField')(default='', max_length=40, blank=True),
                      keep_default=False)

        # Adding field 'ContentMetadata.archive_id'
        db.add_column(u'content_metadata_contentmetadata', 'archive_id',
                      self.gf('django.db.models.fields.CharField')(default='...', max_length=40),
                      keep_default=False)

        # Adding field 'ContentMetadata.activity_id'
        db.add_column(u'content_metadata_contentmetadata', 'activity_id',
                      self.gf('django.db.models.fields.CharField')(default='...', max_length=40),
                      keep_default=False)

        # Adding index on 'ContentMetadata', fields ['content_id']
        db.create_index(u'content_metadata_contentmetadata', ['content_id'])


    def backwards(self, orm):
        # Removing index on 'ContentMetadata', fields ['content_id']
        db.delete_index(u'content_metadata_contentmetadata', ['content_id'])

        # Deleting field 'ContentMetadata.original_id'
        db.delete_column(u'content_metadata_contentmetadata', 'original_id')

        # Deleting field 'ContentMetadata.gallery_id'
        db.delete_column(u'content_metadata_contentmetadata', 'gallery_id')

        # Deleting field 'ContentMetadata.homepage_featured_id'
        db.delete_column(u'content_metadata_contentmetadata', 'homepage_featured_id')

        # Deleting field 'ContentMetadata.archive_id'
        db.delete_column(u'content_metadata_contentmetadata', 'archive_id')

        # Deleting field 'ContentMetadata.activity_id'
        db.delete_column(u'content_metadata_contentmetadata', 'activity_id')


    models = {
        u'content_metadata.contentmetadata': {
            'Meta': {'object_name': 'ContentMetadata'},
            'activity_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'archive_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'content_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True', 'db_index': 'True'}),
            'gallery_id': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'homepage_featured_id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original_id': ('django.db.models.fields.CharField', [], {'max_length': '40'})
        }
    }

    complete_apps = ['content_metadata']
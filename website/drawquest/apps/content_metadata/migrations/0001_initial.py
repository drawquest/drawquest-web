# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ContentMetadata'
        db.create_table(u'content_metadata_contentmetadata', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('content_id', self.gf('django.db.models.fields.BigIntegerField')(unique=True)),
        ))
        db.send_create_signal(u'content_metadata', ['ContentMetadata'])


    def backwards(self, orm):
        # Deleting model 'ContentMetadata'
        db.delete_table(u'content_metadata_contentmetadata')


    models = {
        u'content_metadata.contentmetadata': {
            'Meta': {'object_name': 'ContentMetadata'},
            'content_id': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['content_metadata']
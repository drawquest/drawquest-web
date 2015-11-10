# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Complaint'
        db.create_table('bounces_complaint', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('feedback_type', self.gf('django.db.models.fields.CharField')(max_length=255, blank=True)),
        ))
        db.send_create_signal('bounces', ['Complaint'])


    def backwards(self, orm):
        
        # Deleting model 'Complaint'
        db.delete_table('bounces_complaint')


    models = {
        'bounces.bounce': {
            'Meta': {'object_name': 'Bounce'},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permanent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sub_type': ('django.db.models.fields.SmallIntegerField', [], {})
        },
        'bounces.complaint': {
            'Meta': {'object_name': 'Complaint'},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'feedback_type': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'bounces.suppressedemail': {
            'Meta': {'object_name': 'SuppressedEmail'},
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['bounces']

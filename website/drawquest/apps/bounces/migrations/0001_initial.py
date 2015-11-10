# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'SuppressedEmail'
        db.create_table('bounces_suppressedemail', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.CharField')(unique=True, max_length=255)),
        ))
        db.send_create_signal('bounces', ['SuppressedEmail'])

        # Adding model 'Bounce'
        db.create_table('bounces_bounce', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('permanent', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('sub_type', self.gf('django.db.models.fields.SmallIntegerField')()),
        ))
        db.send_create_signal('bounces', ['Bounce'])


    def backwards(self, orm):
        
        # Deleting model 'SuppressedEmail'
        db.delete_table('bounces_suppressedemail')

        # Deleting model 'Bounce'
        db.delete_table('bounces_bounce')


    models = {
        'bounces.bounce': {
            'Meta': {'object_name': 'Bounce'},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'permanent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sub_type': ('django.db.models.fields.SmallIntegerField', [], {})
        },
        'bounces.suppressedemail': {
            'Meta': {'object_name': 'SuppressedEmail'},
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['bounces']

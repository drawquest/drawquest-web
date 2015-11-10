# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Activity'
        db.create_table(u'activity_activity', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('actor_id', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('timestamp', self.gf('canvas.util.UnixTimestampField')()),
            ('activity_type', self.gf('django.db.models.fields.IntegerField')()),
            ('data', self.gf('django.db.models.fields.TextField')()),
            ('key', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('comment_id', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
            ('quest_id', self.gf('django.db.models.fields.BigIntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'activity', ['Activity'])

        # Adding unique constraint on 'Activity', fields ['activity_type', 'key']
        db.create_unique(u'activity_activity', ['activity_type', 'key'])


    def backwards(self, orm):
        # Removing unique constraint on 'Activity', fields ['activity_type', 'key']
        db.delete_unique(u'activity_activity', ['activity_type', 'key'])

        # Deleting model 'Activity'
        db.delete_table(u'activity_activity')


    models = {
        u'activity.activity': {
            'Meta': {'unique_together': "(('activity_type', 'key'),)", 'object_name': 'Activity'},
            'activity_type': ('django.db.models.fields.IntegerField', [], {}),
            'actor_id': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'comment_id': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'quest_id': ('django.db.models.fields.BigIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {})
        },
        u'activity.legacyactivity': {
            'Meta': {'object_name': 'LegacyActivity'},
            'activity_type': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'data': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {})
        },
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '254', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['activity']
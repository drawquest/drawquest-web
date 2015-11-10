# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'PlaybackData'
        db.delete_table(u'playback_playbackdata')


        # Changing field 'Playback.viewer'
        db.alter_column(u'playback_playback', 'viewer_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['canvas_auth.User']))

    def backwards(self, orm):
        # Adding model 'PlaybackData'
        db.create_table(u'playback_playbackdata', (
            ('comment', self.gf('django.db.models.fields.related.OneToOneField')(related_name='playback_data', unique=True, to=orm['canvas.Comment'])),
            ('blob', self.gf('django.db.models.fields.TextField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('playback', ['PlaybackData'])


        # Changing field 'Playback.viewer'
        db.alter_column(u'playback_playback', 'viewer_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User']))

    models = {
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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'canvas.category': {
            'Meta': {'object_name': 'Category'},
            'description': ('django.db.models.fields.CharField', [], {'max_length': '140'}),
            'founded': ('django.db.models.fields.FloatField', [], {'default': '1298956320'}),
            'founder': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'founded_groups'", 'null': 'True', 'blank': 'True', 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderators': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'moderated_categories'", 'symmetrical': 'False', 'to': u"orm['auth.User']"}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20'}),
            'visibility': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'canvas.comment': {
            'Meta': {'object_name': 'Comment'},
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'attribution_copy': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'attribution_user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'comments'", 'null': 'True', 'blank': 'True', 'to': u"orm['auth.User']"}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'comments'", 'null': 'True', 'blank': 'True', 'to': u"orm['canvas.Category']"}),
            'created_on_iphone': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'default': "'0.0.0.0'", 'max_length': '15'}),
            'judged': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ot_hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'parent_comment': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'replies'", 'null': 'True', 'blank': 'True', 'to': u"orm['canvas.Comment']"}),
            'posted_on_quest_of_the_day': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'replied_comment': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['canvas.Comment']", 'null': 'True', 'blank': 'True'}),
            'reply_content': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'used_in_comments'", 'null': 'True', 'to': u"orm['canvas.Content']"}),
            'reply_text': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'blank': 'True'}),
            'score': ('django.db.models.fields.FloatField', [], {'default': '0', 'db_index': 'True'}),
            'skip_moderation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'star_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True', 'blank': 'True'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '140', 'blank': 'True'}),
            'ugq': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'uuid': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'visibility': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'canvas.content': {
            'Meta': {'object_name': 'Content'},
            'alpha': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'animated': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'default': "'0.0.0.0'", 'max_length': '15'}),
            'remix_of': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'remixes'", 'null': 'True', 'to': u"orm['canvas.Content']"}),
            'remix_text': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '1000', 'blank': 'True'}),
            'source_url': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '4000', 'blank': 'True'}),
            'stamps_used': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'used_as_stamp'", 'blank': 'True', 'to': u"orm['canvas.Content']"}),
            'stroke_count': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {}),
            'url_mapping': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas.ContentUrlMapping']", 'null': 'True', 'blank': 'True'}),
            'visibility': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'canvas.contenturlmapping': {
            'Meta': {'object_name': 'ContentUrlMapping'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'canvas_auth.user': {
            'Meta': {'object_name': 'User', 'db_table': "u'auth_user'", '_ormbases': [u'auth.User'], 'proxy': 'True'}
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'playback.playback': {
            'Meta': {'unique_together': "(('comment', 'viewer'),)", 'object_name': 'Playback'},
            'comment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'playbacks'", 'to': u"orm['canvas.Comment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {'default': '0'}),
            'viewer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas_auth.User']"})
        }
    }

    complete_apps = ['playback']
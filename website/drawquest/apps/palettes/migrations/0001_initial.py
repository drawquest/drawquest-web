# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'ColorPack'
        db.create_table(u'palettes_colorpack', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('cost', self.gf('django.db.models.fields.IntegerField')()),
            ('is_for_sale', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_new', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'palettes', ['ColorPack'])

        # Adding M2M table for field owners on 'ColorPack'
        m2m_table_name = db.shorten_name(u'palettes_colorpack_owners')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('colorpack', models.ForeignKey(orm[u'palettes.colorpack'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['colorpack_id', 'user_id'])

        # Adding model 'Color'
        db.create_table(u'palettes_color', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('red', self.gf('django.db.models.fields.IntegerField')()),
            ('green', self.gf('django.db.models.fields.IntegerField')()),
            ('blue', self.gf('django.db.models.fields.IntegerField')()),
            ('ordinal', self.gf('django.db.models.fields.IntegerField')()),
            ('label', self.gf('django.db.models.fields.CharField')(max_length=50)),
            ('cost', self.gf('django.db.models.fields.IntegerField')()),
            ('is_for_sale', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_new', self.gf('django.db.models.fields.BooleanField')(default=True)),
        ))
        db.send_create_signal(u'palettes', ['Color'])

        # Adding M2M table for field owners on 'Color'
        m2m_table_name = db.shorten_name(u'palettes_color_owners')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('color', models.ForeignKey(orm[u'palettes.color'], null=False)),
            ('user', models.ForeignKey(orm[u'auth.user'], null=False))
        ))
        db.create_unique(m2m_table_name, ['color_id', 'user_id'])


    def backwards(self, orm):
        # Deleting model 'ColorPack'
        db.delete_table(u'palettes_colorpack')

        # Removing M2M table for field owners on 'ColorPack'
        db.delete_table(db.shorten_name(u'palettes_colorpack_owners'))

        # Deleting model 'Color'
        db.delete_table(u'palettes_color')

        # Removing M2M table for field owners on 'Color'
        db.delete_table(db.shorten_name(u'palettes_color_owners'))


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
        u'palettes.color': {
            'Meta': {'object_name': 'Color'},
            'blue': ('django.db.models.fields.IntegerField', [], {}),
            'cost': ('django.db.models.fields.IntegerField', [], {}),
            'green': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_for_sale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_new': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ordinal': ('django.db.models.fields.IntegerField', [], {}),
            'owners': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['canvas_auth.User']", 'symmetrical': 'False'}),
            'red': ('django.db.models.fields.IntegerField', [], {})
        },
        u'palettes.colorpack': {
            'Meta': {'object_name': 'ColorPack'},
            'cost': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_for_sale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_new': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'owners': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['canvas_auth.User']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['palettes']

# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Don't use "from appname.models import ModelName". 
        # Use orm.ModelName to refer to models in this application,
        # and orm['appname.ModelName'] for models in other applications.

        colors = [
            ('White', 255,255,255),
            ('Gray', 184,182,181),
            ('Slate', 74,74,74),
            ('Light Blue', 134,213,255),
            ('Deep Purple', 124,130,255),
            ('Red', 233,90,92),
            ('Orange', 248,172,85),
            ('Yellow', 255,228,92),
            ('Green', 108,214,116),
            ('Sweet Beige', 255,228,177),
            ('Classic Blue', 36,113,247),
            ('Cinnamon Brown', 156,103,95),

            ('Rustic Red', 163,53,14),
            ('Classic Orange', 242,136,0),
            ('Crayon Green', 24,200,38),
            ('Retro Blue', 44,154,213),
            ('Classic Purple', 136,60,237),

            ('Snow Blue', 221,251,253),
            ('Snow Gray', 239,239,239),
            ('Pale Green', 206,225,214),
            ('Conifer Green', 59,121,77),
            ('Cranberry Red', 118,0,0),

            ('Sweet Red', 254,67,101),
            ('Bubblegum Pink', 255,171,187),
            ('Ripe Yellow', 150,255,171),
            ('Electric Blue', 18,238,255),

            ('Pale Beige', 255,233,215),
            ('Pale Pink', 255,224,214),
            ('Pale Salmon', 241,189,171),
            ('Deep Brown', 87,37,30),

            ('Dark Violet', 91,35,105),
            ('Dark Fuchsia', 161,28,71),
            ('Painter Red', 235,30,37),
            ('Dawn Orange', 255,161,0),
            ('Dawn Yellow', 255,227,0),

            ('Apex Blue', 30,66,176),
            ('Sky Blue', 139,220,255),
            ('Horizon Blue', 212,242,255),
            ('Overcast Blue', 182,216,230),

            ('Black', 0,0,0),
            ('Midnight Blue', 2,14,106),
            ('Midnight Purple', 50,2,85),
            ('Midnight Green', 8,51,55),
            ('Starlight Yellow', 255,254,222),

            ('Dusty Brown', 180,152,115),
            ('Camo Brown', 163,107,62),
            ('Camo Green', 107,127,53),
            ('Mud Brown', 109,75,47),

            ('Neon Yellow', 255,253,69),
            ('Neon Green', 0,255,48),
            ('Bright Teal', 0,255,210),
            ('Neon Fuchsia', 255,9,235),
        ]

        for label, r, g, b in colors:
            print label
            color = orm.Color.objects.get(red=r, green=g, blue=b)
            color.label = label
            color.save()


    def backwards(self, orm):
        "Write your backwards methods here."

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
            'Meta': {'ordering': "['ordinal']", 'object_name': 'Color'},
            'blue': ('django.db.models.fields.IntegerField', [], {}),
            'cost': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'green': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_for_sale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_new': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'ordinal': ('django.db.models.fields.IntegerField', [], {}),
            'owned_by_default': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'owners': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['canvas_auth.User']", 'symmetrical': 'False'}),
            'red': ('django.db.models.fields.IntegerField', [], {})
        },
        u'palettes.colorpack': {
            'Meta': {'ordering': "['ordinal']", 'object_name': 'ColorPack'},
            'colors': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['palettes.Color']", 'symmetrical': 'False'}),
            'cost': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_for_sale': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_new': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'legacy_palette_name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '20', 'blank': 'True'}),
            'ordinal': ('django.db.models.fields.IntegerField', [], {}),
            'owners': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['canvas_auth.User']", 'symmetrical': 'False'})
        }
    }

    complete_apps = ['palettes']
    symmetrical = True

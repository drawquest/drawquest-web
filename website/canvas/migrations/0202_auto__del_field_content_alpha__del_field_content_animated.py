# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Content.alpha'
        db.delete_column(u'canvas_content', 'alpha')

        # Deleting field 'Content.animated'
        db.delete_column(u'canvas_content', 'animated')


    def backwards(self, orm):
        # Adding field 'Content.alpha'
        db.add_column(u'canvas_content', 'alpha',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'Content.animated'
        db.add_column(u'canvas_content', 'animated',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)


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
        u'canvas.apiapp': {
            'Meta': {'object_name': 'APIApp'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'})
        },
        u'canvas.apiauthtoken': {
            'Meta': {'unique_together': "(('user', 'app'),)", 'object_name': 'APIAuthToken'},
            'app': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas.APIApp']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'token': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '40'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
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
            'score': ('django.db.models.fields.FloatField', [], {'default': '0', 'db_index': 'True'}),
            'skip_moderation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'star_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True', 'blank': 'True'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {'default': '0'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '140', 'blank': 'True'}),
            'ugq': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'uuid': ('django.db.models.fields.IntegerField', [], {'db_index': 'True', 'null': 'True', 'blank': 'True'}),
            'visibility': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        u'canvas.commentflag': {
            'Meta': {'object_name': 'CommentFlag'},
            'comment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flags'", 'to': u"orm['canvas.Comment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {}),
            'type_id': ('django.db.models.fields.IntegerField', [], {}),
            'undone': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flags'", 'to': u"orm['auth.User']"})
        },
        u'canvas.commentmoderationlog': {
            'Meta': {'object_name': 'CommentModerationLog'},
            'comment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas.Comment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'moderated_comments_log'", 'to': u"orm['auth.User']"}),
            'visibility': ('django.db.models.fields.IntegerField', [], {})
        },
        u'canvas.commentpin': {
            'Meta': {'object_name': 'CommentPin'},
            'auto': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'comment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas.Comment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'canvas.commentsticker': {
            'Meta': {'object_name': 'CommentSticker'},
            'comment': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'stickers'", 'to': u"orm['canvas.Comment']"}),
            'epic_message': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '140', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {}),
            'type_id': ('django.db.models.fields.IntegerField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'canvas.commentstickerlog': {
            'Meta': {'object_name': 'CommentStickerLog'},
            'comment': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas.Comment']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'canvas.content': {
            'Meta': {'object_name': 'Content'},
            'id': ('django.db.models.fields.CharField', [], {'max_length': '40', 'primary_key': 'True'}),
            'ip': ('django.db.models.fields.IPAddressField', [], {'default': "'0.0.0.0'", 'max_length': '15'}),
            'remix_of': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'remixes'", 'null': 'True', 'to': u"orm['canvas.Content']"}),
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
        u'canvas.emailunsubscribe': {
            'Meta': {'object_name': 'EmailUnsubscribe'},
            'email': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        u'canvas.facebookinvite': {
            'Meta': {'object_name': 'FacebookInvite'},
            'fb_message_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invited_fbid': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'invitee': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'facebook_invited_from'", 'null': 'True', 'blank': 'True', 'to': u"orm['auth.User']"}),
            'inviter': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'related_name': "'facebook_sent_invites'", 'null': 'True', 'blank': 'True', 'to': u"orm['auth.User']"})
        },
        u'canvas.facebookuser': {
            'Meta': {'object_name': 'FacebookUser'},
            'email': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'fb_uid': ('django.db.models.fields.BigIntegerField', [], {'unique': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'gender': ('django.db.models.fields.PositiveSmallIntegerField', [], {'default': '0'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invited_by': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['canvas.FacebookUser']", 'symmetrical': 'False', 'blank': 'True'}),
            'last_invited': ('canvas.util.UnixTimestampField', [], {'default': '0'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True', 'null': 'True', 'blank': 'True'})
        },
        u'canvas.followcategory': {
            'Meta': {'unique_together': "(('user', 'category'),)", 'object_name': 'FollowCategory'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'followers'", 'to': u"orm['canvas.Category']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'following'", 'to': u"orm['auth.User']"})
        },
        u'canvas.friendjoinednotificationreceipt': {
            'Meta': {'unique_together': "(('actor', 'recipient'),)", 'object_name': 'FriendJoinedNotificationReceipt'},
            'actor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'+'", 'to': u"orm['auth.User']"})
        },
        u'canvas.stashcontent': {
            'Meta': {'object_name': 'StashContent'},
            'content': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas.Content']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        },
        u'canvas.userinfo': {
            'Meta': {'object_name': 'UserInfo'},
            'avatar': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas.Content']", 'null': 'True'}),
            'bio_text': ('django.db.models.fields.CharField', [], {'max_length': '2000', 'blank': 'True'}),
            'email_hash': ('django.db.models.fields.CharField', [], {'max_length': '40'}),
            'enable_timeline': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'enable_timeline_posts': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'facebook_id': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'follower_count': ('django.db.models.fields.IntegerField', [], {'default': '0', 'blank': 'True'}),
            'free_invites': ('django.db.models.fields.IntegerField', [], {'default': '10'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invite_bypass': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255', 'blank': 'True'}),
            'is_qa': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'post_anonymously': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'profile_image': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['canvas.Comment']", 'null': 'True'}),
            'trust_changed': ('canvas.util.UnixTimestampField', [], {'null': 'True', 'blank': 'True'}),
            'trusted': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'canvas.usermoderationlog': {
            'Meta': {'object_name': 'UserModerationLog'},
            'action': ('django.db.models.fields.IntegerField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'moderator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True'}),
            'note': ('django.db.models.fields.TextField', [], {}),
            'timestamp': ('canvas.util.UnixTimestampField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'moderation_log'", 'to': u"orm['auth.User']"})
        },
        u'canvas.userwarning': {
            'Meta': {'object_name': 'UserWarning'},
            'comment': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['canvas.Comment']", 'null': 'True', 'blank': 'True'}),
            'confirmed': ('canvas.util.UnixTimestampField', [], {'default': '0'}),
            'custom_message': ('django.db.models.fields.TextField', [], {}),
            'disable_user': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'issued': ('canvas.util.UnixTimestampField', [], {}),
            'stock_message': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'user_warnings'", 'to': u"orm['auth.User']"}),
            'viewed': ('canvas.util.UnixTimestampField', [], {'default': '0'})
        },
        u'canvas.welcomeemailrecipient': {
            'Meta': {'object_name': 'WelcomeEmailRecipient'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'recipient': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['canvas']
import datetime
from plistlib import *
import time
from StringIO import StringIO

from django.core.files.base import File

from canvas import json
from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff, create_quest, create_quest_comment, create_current_quest,)
from services import Services, override_service


class TestPlayback(CanvasTestCase):
    def after_setUp(self):
        self.quest = create_current_quest()
        self.content = create_content()

    def _post(self, user=None, quest=None, **kwargs):
        if user is None:
            user = create_user()

        params = {
            'quest_id': self.quest.id,
            'content_id': self.content.id,
        }
        params.update(kwargs)
        return self.api_post('/api/quest_comments/post', params, user=user)['comment']

    def _check(self, cmt_id, playback_data):
        resp = self.api_post('/api/playback/playback_data', {'comment_id': cmt_id})
        self.assertAPISuccess(resp)
        self.assertEqual(json.loads(resp['playback_data']), json.loads(playback_data))

    def test_playback_data(self):
        data = json.dumps({'foo': 'bar'})
        self._check(create_quest_comment(playback_data=data).id, data)

    def test_reactions_update_on_playback(self):
        cmt = create_quest_comment()
        self.assertEqual(len(cmt.details().reactions), 0)
        cmt = self.api_post('/api/playback/playback', {'comment_id': cmt.id})['comment']
        self.assertEqual(len(cmt['reactions']), 1)

    def test_set_playback_data_without_comment_id(self):
        resp = self.api_post('/api/playback/set_playback_data')
        self.assertAPIFailure(resp)

    def test_set_playback_data_api(self):
        user = create_user()
        cmt = self._post(user=user)
        playback = '{"1": 2}'
        resp = self.post('/api/playback/set_playback_data', data={
            'comment_id': cmt['id'],
            'playback_data': playback,
        }, user=user)

        self._check(cmt['id'], playback)

    def test_set_plist_playback_data(self):
        user = create_user()
        cmt = self._post(user=user)

        playback = '{1: 2}'
        p = dict(
            aString="Doodah",
            aList=["A", "B", 12, 32.1, [1, 2, 3]],
            aFloat = 0.1,
            anInt = 728,
        )
        s = StringIO()
        pl = writePlist(p, s)
        s.seek(0)
        
        resp = self.post('/api/playback/set_playback_data', data={
            'comment_id': cmt['id'],
            'playback_plist_data': File(s, 'whatever.xml'),
        }, user=user)

        self._check(cmt['id'], json.backend_dumps(p))


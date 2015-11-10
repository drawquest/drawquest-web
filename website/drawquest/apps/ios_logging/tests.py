import time

from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff, create_quest, create_quest_comment)
from services import Services, override_service


class TestLogging(CanvasTestCase):
    def test_bulk_log(self):
        resp = self.api_post('/api/ios_logging/bulk_log', data={'records': [[time.time(), 'INFO', 'msg']]})
        self.assertAPISuccess(resp)


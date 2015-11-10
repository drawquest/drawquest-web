import time

from drawquest.tests.tests_helpers import (CanvasTestCase, create_content, create_user, create_group,
                                           create_comment, create_staff, create_quest, create_quest_comment)
from drawquest.apps.explore.models import explore_comment_details
from services import Services, override_service


class TestExploreDrawings(CanvasTestCase):
    pass
    #def test_comment_details(self):
    #    cmt = create_quest_comment()
    #    cmts = explore_comment_details()

    #    self.assertFalse(cmt.id in [c['id'] for c in cmts])

    #    cmt.timestamp = time.time() - 60*60*15
    #    cmt.save()
    #    cmts = explore_comment_details()
    #    self.assertTrue(cmt.id in [c['id'] for c in cmts])


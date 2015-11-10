from django.core.exceptions import PermissionDenied
from django.db import models

from canvas.exceptions import ServiceError
from canvas.redis_models import RedisSet, RedisLastBumpedBuffer, RealtimeChannel
from canvas.notifications.actions import Actions
from canvas.url_util import verify_first_party_url
from drawquest.apps.quests.details_models import QuestDetails


class InvitedQuests(RedisLastBumpedBuffer):
    def __init__(self, user):
        try:
            user_id = user.id
        except AttributeError:
            user_id = user

        super(InvitedQuests, self).__init__('user:{}:invited_quests'.format(user_id), None)
        self.user_id = user_id

    def add_invite(self, quest):
        self.bump(quest.id, truncate=False)

        RealtimeChannel('user:{}:rt_tab_badges'.format(self.user_id), 1).publish({'tab_badge_update': 'draw'})

    def _invites(self, invited_quests):
        if not invited_quests:
            return []

        ids, timestamps = zip(*invited_quests)
        return zip(QuestDetails.from_ids(ids), timestamps)

    def invites(self):
        return self._invites(list(self.with_scores[:]))

    def uncompleted_invites(self):
        from drawquest.apps.quests.models import completed_quest_ids

        return self._invites([
            (id_, ts)
            for id_, ts in self.with_scores[:]
            if long(id_) not in completed_quest_ids(self.user_id)
        ])


class InvitedUsers(RedisSet):
    def __init__(self, quest):
        super(InvitedUsers, self).__init__('quest:{}:invited_users'.format(quest.id))
        self.quest = quest

    def invite(self, inviter, invitees, type='invite', ignore_errors=False):
        if not ignore_errors:
            for invitee in invitees:
                if invitee.id in self:
                    raise ServiceError("User {} has already been invited.".format(invitee.username))
                if invitee.id == inviter.id:
                    raise ServiceError("You can't invite yourself - you're already here!")
                if self.quest.author == invitee:
                    raise ServiceError("That user is already in this quest.")

        self.sadd([invitee.id for invitee in invitees])

        for invitee in invitees:
            Actions.invite_user(inviter, self.quest, invitee)
            invitee.redis.quest_invites.add_invite(self.quest)


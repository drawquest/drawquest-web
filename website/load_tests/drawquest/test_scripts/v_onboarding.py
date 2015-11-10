import time

from utils import *

# quest ID 7005 -> '47',  45 drawings
# quest ID 7002 -> '44',  95 drawings
# quest ID 7004 -> '46', 145 drawings

class Transaction(DrawquestTransaction):
    def run(self):
        api = ApiConsumer()

        t1 = time.time()

        # Onboarding flow.
        api.heavy_state_sync()
        onboarding_quest = api.onboarding_quest()
        #api.call('quest_comments/rewards_for_posting', {'quest_id': onboarding_quest['quest']['id']})
        api.signup()
        #api.heavy_state_sync()
        #api.quest_comments(onboarding_quest['quest']['id'])
        #TODO upload
        for _ in range(145):
            print api.call('quest_comments/post', {
                'quest_id': QUEST_ID,
                #'content_id': '66c7f508180e0dab0b573792a56b0fc7beefbd2b',
                'content_id': '0d9c1c0ee540bfb2a6bd55e3abfbf44617ad0bea',
            }) #TODO use uploaded one.
        #TODO api.call('playback/set_playback_data')
        api.heavy_state_sync()

        # Taps basement icon.
        #api.call('activity/activities')

        # Taps Quests (Quest Homepage).
        #api.call('quests/current')
        #api.call('quests/archive')

        latency = time.time() - t1
        self.custom_timers['Onboarding_Timer'] = latency

if __name__ == '__main__':
    main(Transaction)


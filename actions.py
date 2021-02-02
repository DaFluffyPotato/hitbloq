import time

from db import database
from user import User
import cr

def process_action(action):
    if action['type'] == 'add_user':
        u = User().create(database, action['user_id'])
        if u:
            u.refresh_scores(database, action['_id'])
        else:
            print('error on user add', action['user_id'])

    if action['type'] == 'update_user':
        try:
            u = database.get_users([action['user_id']])[0]
            u.refresh_scores(database, action['_id'])
        except IndexError:
            print('Invalid user for update:', action['user_id'])

    if action['type'] == 'recalculate_cr':
        cr.full_cr_update(action['map_pools'], action['_id'])

    if action['type'] == 'rank_song':
        database.rank_song(action['song_id'], action['map_pool'])

    if action['type'] == 'unrank_song':
        database.unrank_song(action['song_id'], action['map_pool'])

    if action['type'] == 'update_rank_histories':
        database.update_rank_histories(action['map_pool'], action['_id'])

    database.clear_action(action['_id'])

if __name__ == "__main__":
    while True:
        next_action = database.get_next_action()

        if next_action:
            print('processing action', next_action['type'])
            process_action(next_action)
        else:
            time.sleep(3)

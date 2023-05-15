import time
import os

from db import database
import create_action

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR

USER_UPDATE_BATCH = 3000

user_update_cycle = 0

timer = 1
while True:
    if timer % (DAY * 7) == 0:
        if len(list(database.get_actions())) < 20:
            user_ids = [i for i in range(database.get_counter('user_id')['count'])]
            total_users = len(user_ids)

            # slice subsection of users for update
            user_ids = user_ids[user_update_cycle * USER_UPDATE_BATCH : (user_update_cycle + 1) * USER_UPDATE_BATCH]

            user_update_cycle += 1
            if user_update_cycle * USER_UPDATE_BATCH > total_users:
                user_update_cycle = 0

            if len(user_ids):
                print('updating users', user_ids[0], 'to', user_ids[-1])

            create_action.update_users(user_ids)
    if timer % (DAY) == 0:
        for pool_id in database.get_pool_ids(False):
            create_action.recalculate_cr([pool_id])
            if timer != 0: # skip player history updates if rebooting regular tasks
                create_action.update_rank_histories(pool_id)
        create_action.regenerate_playlists()

    if timer % (DAY * 7) == 0:
        create_action.refresh_pool_popularity()
        create_action.refresh_profiles()
        os.system('service nginx restart')

    time.sleep(1)
    timer += 1

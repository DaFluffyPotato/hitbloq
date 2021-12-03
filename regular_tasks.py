import time

from db import database
import create_action

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR

timer = 0
while True:
    if timer % (DAY * 7) == 0:
        if len(list(database.get_actions())) < 20:
            user_ids = [i for i in range(database.get_counter('user_id')['count'])]
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

    time.sleep(1)
    timer += 1

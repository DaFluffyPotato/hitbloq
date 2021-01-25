import time

from db import database
import create_action

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR

timer = 0
while True:
    if timer % (MINUTE * 15) == 0:
        if len(list(database.get_actions())) < 20:
            user_ids = [i for i in range(database.get_counter('user_id')['count'])]
            create_action.update_users(user_ids)
    if timer % (DAY) == 0:
        for pool_id in database.get_pool_ids(False):
            create_action.recalculate_cr([pool_id])
    time.sleep(1)
    timer += 1

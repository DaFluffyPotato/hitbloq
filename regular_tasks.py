import time

from db import database
import create_action

MINUTE = 60
HOUR = 60 * MINUTE
DAY = 24 * HOUR

timer = 0
while True:
    if timer % (MINUTE * 15) == 0:
        if len(list(database.get_actions())) == 0:
            user_ids = [i for i in range(database.get_counter('user_id')['count'])]
            create_action.update_users(user_ids)
    if timer % (DAY) == 0:
        create_action.recalculate_cr(database.get_pool_ids(False))
    time.sleep(1)
    timer += 1

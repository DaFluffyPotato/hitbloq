from db import database

leaderboards = database.search_leaderboards({})

delete_ids = []
for leaderboard in leaderboards:
    if leaderboard['_id'].split('|')[0].upper() != leaderboard['_id'].split('|')[0]:
        delete_ids.append(leaderboard['_id'])

database.db['leaderboards'].delete_many({'_id': {'$in': delete_ids}})

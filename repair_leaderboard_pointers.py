import sys

from db import database

leaderboard_id = sys.argv[1]

def repair_leaderboard_pointers(leaderboard_id):
    leaderboard_scores = list(database.db['scores'].find({'song_id': leaderboard_id}))

    leaderboard_scores.sort(key=lambda x: x['score'], reverse=True)
    leaderboard_score_ids = [score['_id'] for score in leaderboard_scores]
    print(leaderboard_score_ids[:10])

    if len(leaderboard_scores):
        print('found scores and updating leaderboard')
        database.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$set': {'score_ids': leaderboard_score_ids}})
    else:
        print('no scores found')

repair_leaderboard_pointers(leaderboard_id)
print('done!')

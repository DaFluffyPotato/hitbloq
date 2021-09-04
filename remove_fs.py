import scoresaber
from db import database
import user as user_mod

matching_leaderboards = list(set(database.db['ranked_lists'].find_one({'_id': 'paul'})['leaderboard_id_list'] + database.db['ranked_lists'].find_one({'_id': 'funny_haha_pauls'})['leaderboard_id_list']))

matching_scores = []

leaderboards = list(database.db['leaderboards'].find({'_id': {'$in': matching_leaderboards}}))
for leaderboard in leaderboards:
    check_amt = int(len(leaderboard['score_ids']) * 0.2)
    if len(leaderboard['score_ids']) < 10:
        check_amt = len(leaderboard['score_ids'])
    matching_scores += leaderboard['score_ids'][:check_amt]

scores = list(database.db['scores'].find({'_id': {'$in': matching_scores}}))

scores_by_id = {score['song_id'] + str(score['score']) : score for score in scores}
print(len(scores_by_id))

users = {}

for score in scores:
    if score['user'] not in users:
        users[score['user']] = score['time_set']
    else:
        users[score['user']] = min(score['time_set'], users[score['user']])

user_data = list(database.db['users'].find({'_id': {'$in': list(users.keys())}}))

ss = scoresaber.ScoresaberInterface(database)

for user in user_data:
    data = ss.fetch_until(user['scoresaber_id'], users[user['_id']] - 100)
    for score in data:
        score_id = score['songHash'].upper() + '|' + score['difficultyRaw'] + str(score['unmodififiedScore'])
        if score_id in scores_by_id:
            if score['mods'] != '':
                print('Found mods', score['mods'])
                print('deleting score:', score_id)
                matching_score = scores_by_id[score_id]
                database.db['leaderboards'].update_one({'_id': matching_score['song_id']}, {'$pull': {'score_ids': matching_score['_id']}})
                database.db['scores'].delete_one({'_id': matching_score['_id']})
                print('removed!')
    database.delete_user_null_pointers(user_mod.User().load(user))

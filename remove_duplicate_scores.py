from db import database

scores = list(database.db['scores'].find({}))
print('scores downloaded')

scores_map = {}
for score in scores:
    score_id = (score['song_id'], score['user'])
    if score_id not in scores_map:
        scores_map[score_id] = [score]
    else:
        scores_map[score_id].append(score)

remove_list = []
for score_id in scores_map:
    if len(scores_map[score_id]) > 1:
        best_score = (scores_map[score_id][0]['score'], scores_map[score_id][0]['_id'])
        for score in scores_map[score_id]:
            if score['score'] > best_score[0]:
                best_score = (score['score'], score['_id'])
        for score in scores_map[score_id]:
            if score['_id'] != best_score[1]:
                remove_list.append(score['_id'])

print(len(remove_list))
database.db['scores'].delete_many({'_id': {'$in': remove_list}})
print('done')

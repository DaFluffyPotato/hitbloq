import pymongo
from db import database

leaderboards = list(database.db['leaderboards'].find({}))
for i, leaderboard in enumerate(leaderboards):
    if leaderboard['cover']:
        new_cover = 'https://cdn.beatsaver.com/' + leaderboard['cover'].split('/')[-1].replace('png', 'jpg')
        database.db['leaderboards'].update_one({'_id': leaderboard['_id']}, {'$set': {'cover': new_cover}})
        print(i, '/', len(leaderboards))

'''
broken = [
    '07D36C6FED15FEEB5A85AAA8D8E1FAFB7283947C|_ExpertPlus_SoloStandard',
    'ED90CC573FB9AC5FB86FF63CA9BCB723BBB01BC3|_ExpertPlus_SoloStandard',
    '03A4575B6FE87F1E79C1664464D482A2FF8E0780|_ExpertPlus_SoloStandard',
    '8A1DF046CE6737D7199676990FC19B78E067A3EB|_ExpertPlus_SoloStandard',
    '03A4575B6FE87F1E79C1664464D482A2FF8E0780|_Expert_SoloStandard',
    '5A8377CEC04DAAC76A525CF810156AC6456D1F1F|_Hard_SoloStandard',
    '5A8377CEC04DAAC76A525CF810156AC6456D1F1F|_Normal_SoloStandard',
    '9EC4BBF552797685DF73033C04CF487737097A7D|_ExpertPlus_SoloStandard',
    '6DD22DDEBE42D403BD585EF2CFBE772E931F2D65|_Expert_SoloStandard',
    '5F4F010301806CF47F0ACE06DEADF9D321B06DAC|_ExpertPlus_SoloStandard',
]

for rl in database.db['ranked_lists'].find({}):
    for i, lb in enumerate(rl['leaderboard_id_list']):
        fixed_id = lb.split('|')[0].upper() + '|' + lb.split('|')[1]
        if fixed_id != lb:
            print('id', fixed_id, lb, rl['shown_name'], i)
        if lb in broken:
            print('oops', lb, rl['shown_name'])


leaderboards = database.db['leaderboards'].find({})

fix = [(leaderboard['hash'], leaderboard['_id'], leaderboard) for leaderboard in leaderboards if leaderboard['hash'].lower() == leaderboard['hash']]

print(len(fix))
for i, f in enumerate(fix):
    print(str(i + 1), '/', len(fix))
    hash = f[0].upper()
    new_id = f[1].split('|')[0].upper() + '|' + f[1].split('|')[1]
    old_id = f[1]
    f[2]['_id'] = new_id
    f[2]['hash'] = hash
    associated_scores = list(database.db['scores'].find({'song_id': f[1]}))
    print(new_id)
    print(len(associated_scores))
    for score in associated_scores:
        database.db['scores'].update_one({'_id': score['_id']}, {'$set': {'song_id': new_id}})
    #print(len(associated_scores), 'scores')
    #print(associated_scores[0])
    print(new_id)
    try:
        database.db['leaderboards'].insert_one(f[2])
    except pymongo.errors.DuplicateKeyError:
        print('DUPE:', new_id)
        dupe = database.db['leaderboards'].find_one({'_id': f[2]['_id']})
        if len(f[2]['score_ids']) > len(dupe['score_ids']):
            print('lower has more scores --- replacing...')
            database.db['leaderboards'].delete_one({'_id': f[2]['_id']})
            database.db['leaderboards'].insert_one(f[2])
        else:
            print('higher has more scores --- keeping original...')
        print(len(f[2]['score_ids']), ' --- ', len(dupe['score_ids']))
    database.db['leaderboards'].delete_one({'_id': old_id})
'''

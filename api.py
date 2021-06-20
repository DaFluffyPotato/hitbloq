import json

from flask import jsonify

from db import database
from general import mongo_clean
import create_action

RANKED_LIST_DESCRIPTION = 'A collection of maps from the <map_pool_name> Hitbloq map pool used for the associated ranked ladder. Check out https://hitbloq.com for more info.'

def action_list():
    resp = list(database.get_actions())
    for action in resp:
        del action['_id']
    return jsonify(resp)

def add_user(request_json, ip_address):
    ratelimits = database.get_rate_limits(ip_address)
    if ratelimits['user_additions'] < 2:
        database.ratelimit_add(ip_address, 'user_additions')
        create_action.create_user(request_json['url'])
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'ratelimit'})

def ranked_list(pool_id, offset=0, count=30):
    ranked_list_data = database.get_ranked_list(mongo_clean(pool_id))
    ranked_list_data['leaderboard_id_list'] = ranked_list_data['leaderboard_id_list'][offset:offset + count]
    return jsonify(ranked_list_data)

def ranked_lists():
    return jsonify(database.get_pool_ids(False))

def get_announcement():
    return jsonify(database.db['config'].find_one({'_id': 'announcement'}))

def get_map_pools_detailed():
    map_pools = database.get_ranked_lists()

    response = []
    for pool in map_pools:
        response.append({
            'title': pool['shown_name'],
            'author': 'Hitbloq',
            #'image': pool['cover'],
            'image': 'https://hitbloq.com/static/hitbloq.png',
            'id': pool['_id'],
            'description': RANKED_LIST_DESCRIPTION.replace('<map_pool_name>', pool['shown_name']),
            'download_url': 'https://hitbloq.com/static/hashlists/' + pool['_id'] + '.bplist'
        })

    return jsonify(response)

def get_leaderboard_info(leaderboard_id):
    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    leaderboard_data['_id'] = str(leaderboard_data['_id'])
    del leaderboard_data['score_ids']
    print(leaderboard_data)
    return jsonify(leaderboard_data)

def get_leaderboard_scores(leaderboard_id, offset=0, count=30):
    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    score_ids = leaderboard_data['score_ids']
    score_data = list(database.fetch_scores(score_ids).sort('score', -1))[offset:offset + count]
    for score in score_data:
        del score['_id']
    return jsonify(score_data)

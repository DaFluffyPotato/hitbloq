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

def ranked_list(pool_id):
    return jsonify(database.get_ranked_list(mongo_clean(pool_id)))

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
            'image': pool['cover'],
            'id': pool['_id'],
            'description': RANKED_LIST_DESCRIPTION.replace('<map_pool_name>', pool['shown_name']),
            'download_url': 'https://hitbloq.com/api/ranked_list/' + pool['_id'],
        })

    return jsonify(response)

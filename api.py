from flask import jsonify

from db import database
from general import mongo_clean
import create_action

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

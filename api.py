import json

from flask import jsonify

from db import database
from general import mongo_clean, max_score
import create_action

RANKED_LIST_DESCRIPTION = 'A collection of maps from the <map_pool_name> Hitbloq map pool used for the associated ranked ladder. Check out https://hitbloq.com for more info.'

def action_list():
    resp = list(database.get_actions(queue_id=-1))
    for action in resp:
        action['_id'] = str(action['_id'])
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
    print(leaderboard_data)
    return jsonify(leaderboard_data)

def get_leaderboard_scores(leaderboard_id, offset=0, count=30):
    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    score_data = list(database.db['scores'].find({'song_id': leaderboard_data['_id']}).sort('score', -1))[offset:offset + count]
    for score in score_data:
        del score['_id']
    return jsonify(score_data)

def get_leaderboard_scores_extended(leaderboard_id, offset=0, count=10):
    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    score_data = list(database.db['scores'].find({'song_id': leaderboard_data['_id']}).sort('score', -1))[offset:offset + count]
    user_list = [score['user'] for score in score_data]
    user_data = {user.id : user for user in database.get_users(user_list)}
    for i, score in enumerate(score_data):
        del score['_id']
        score['username'] = user_data[score['user']].username
        score['accuracy'] = round(score['score'] / max_score(leaderboard_data['notes']) * 100, 2)
        score['rank'] = offset + i + 1

    return jsonify(score_data)

def get_leaderboard_scores_nearby(leaderboard_id, user):
    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    score_data = list(database.db['scores'].find({'song_id': leaderboard_data['_id']}).sort('score', -1))

    matched_index = -1
    for i, score in enumerate(score_data):
        if score['user'] == user:
            matched_index = i
    if matched_index == -1:
        return jsonify({})
    base_index = max(0, matched_index - 4)

    score_data = score_data[base_index : base_index + 10]

    user_list = [score['user'] for score in score_data]
    user_data = {user.id : user for user in database.get_users(user_list)}
    for i, score in enumerate(score_data):
        del score['_id']
        score['username'] = user_data[score['user']].username
        score['accuracy'] = round(score['score'] / max_score(leaderboard_data['notes']) * 100, 2)
        score['rank'] = base_index + i + 1

    return jsonify(score_data)

def ss_to_hitbloq_id(ss_id):
    matching_user = database.db['users'].find_one({'scoresaber_id': ss_id})
    if matching_user:
        return jsonify({'id': matching_user['_id']})
    else:
        return jsonify({'id': -1})

def player_rank_api(pool_id, user):
    users = database.get_users([user])
    pool_data = database.get_ranked_list(pool_id)

    player_rank = 0
    player_name = None
    player_cr = 0
    player_tier = 'none'
    player_scores = 0
    if len(users):
        user = users[0]
        user.load_pool_scores(database, pool_id)
        player_scores = len(user.scores)
        player_name = user.username
        if pool_id in user.cr_totals:
            player_rank = database.get_user_ranking(user, pool_id)
            player_cr = user.cr_totals[pool_id]

        if pool_data:
            player_rank_ratio = (player_rank - 1) / pool_data['player_count']
            if not len(user.scores):
                player_tier = 'none'
            elif player_rank_ratio < 0.001:
                player_tier = 'myth'
            elif player_rank_ratio < 0.01:
                player_tier = 'master'
            elif player_rank_ratio < 0.05:
                player_tier = 'diamond'
            elif player_rank_ratio < 0.1:
                player_tier = 'platinum'
            elif player_rank_ratio < 0.2:
                player_tier = 'gold'
            elif player_rank_ratio < 0.5:
                player_tier = 'silver'
            else:
                player_tier = 'bronze'

    response = {
        'username': player_name,
        'rank': player_rank,
        'cr': player_cr,
        'tier': 'default/' + player_tier,
        'ranked_score_count': player_scores,
    }

    return jsonify(response)

def user_basic_api(user_id):
    try:
        user = database.get_users([user_id])[0]
        user_data = user.jsonify()
        return jsonify(user_data)
    except IndexError:
        return jsonify({})

def action_id_status(action_id):
    exists = database.action_exists(action_id)
    return jsonify({'exists': exists})

def ss_registered(ss_id):
    matching_user = database.db['users'].find_one({'scoresaber_id': ss_id})
    if matching_user:
        if matching_user['last_update'] != 0:
            return jsonify({'registered': True, 'user': matching_user['_id']})
        else:
            return jsonify({'registered': False, 'user': matching_user['_id']})
    return jsonify({'registered': False, 'user': None})

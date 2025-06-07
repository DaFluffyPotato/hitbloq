from flask import request, make_response, jsonify

from db import database
import beatsaver
import create_action
from general import invalid_curve_data
from cr_formulas import curves

beatsaver_interface = beatsaver.BeatSaverInterface()

def create_pool_api_endpoints(app):
    @app.route('/api/pools/rank', methods=['POST'])
    def pool_rank():
        error = check_for_fields(request.json, ['key', 'pool', 'song'])
        if error:
            return jsonify(error)
        if valid_pool_key(request.json['key'], request.json['pool']):
            database.db['pool_api_logs'].insert_one(request.json)
            return jsonify(pool_rank_cmd(request.json['song'], request.json['pool']))
        return jsonify({'status': 'invalid pool/key pair'})
    
    @app.route('/api/pools/unrank', methods=['POST'])
    def pool_unrank():
        error = check_for_fields(request.json, ['key', 'pool', 'song'])
        if error:
            return jsonify(error)
        if valid_pool_key(request.json['key'], request.json['pool']):
            database.db['pool_api_logs'].insert_one(request.json)
            return jsonify(pool_unrank_cmd(request.json['song'], request.json['pool']))
        return jsonify({'status': 'invalid pool/key pair'})
    
    @app.route('/api/pools/set_manual', methods=['POST'])
    def pool_set_manual():
        error = check_for_fields(request.json, ['key', 'pool', 'song', 'rating'])
        if error:
            return jsonify(error)
        if valid_pool_key(request.json['key'], request.json['pool']):
            database.db['pool_api_logs'].insert_one(request.json)
            return jsonify(pool_set_manual_cmd(request.json['song'], request.json['pool'], float(request.json['rating'])))
        return jsonify({'status': 'invalid pool/key pair'})
    
    @app.route('/api/pools/set_automatic', methods=['POST'])
    def pool_set_automatic():
        error = check_for_fields(request.json, ['key', 'pool', 'song'])
        if error:
            return jsonify(error)
        if valid_pool_key(request.json['key'], request.json['pool']):
            database.db['pool_api_logs'].insert_one(request.json)
            return jsonify(pool_set_automatic_cmd(request.json['song'], request.json['pool']))
        return jsonify({'status': 'invalid pool/key pair'})
    
    @app.route('/api/pools/recalculate_cr', methods=['POST'])
    def pool_recalculate_cr():
        error = check_for_fields(request.json, ['key', 'pool'])
        if error:
            return jsonify(error)
        if valid_pool_key(request.json['key'], request.json['pool']):
            database.db['pool_api_logs'].insert_one(request.json)
            create_action.recalculate_cr([request.json['pool']], queue_id=0)
            return jsonify({'status': 'success'})
        return jsonify({'status': 'invalid pool/key pair'})
    
    @app.route('/api/pools/set_curve', methods=['POST'])
    def pool_set_curve():
        error = check_for_fields(request.json, ['key', 'pool', 'curve'])
        if error:
            return jsonify(error)
        if valid_pool_key(request.json['key'], request.json['pool']):
            database.db['pool_api_logs'].insert_one(request.json)
            return jsonify(pool_set_curve_cmd(request.json['pool'], request.json['curve']))
        return jsonify({'status': 'invalid pool/key pair'})
    
def check_for_fields(json_data, fields):
    for field in fields:
        if field not in json_data:
            return {'status': 'missing parameter', 'error': 'missing ' + field}

def valid_pool_key(request_key, pool_id):
    if pool_id in database.get_pool_ids(True):
        pool_data = database.db['ranked_lists'].find_one({'_id': pool_id})
        if (pool_data['api_key'] == request_key) and request_key:
            return True
    return False

def pool_rank_cmd(song_id, pool_id):
    if pool_id in database.get_pool_ids(True):
        song_data, bs_error = beatsaver_interface.verify_song_id(song_id)
        if song_data:
            create_action.rank_song(song_id, pool_id)
            return {'status': 'success'}
        else:
            if len(song_id.split('|')) == 2:
                return {'status': 'invalid song ID', 'error': bs_error, 'url': 'https://beatsaver.com/api/maps/hash/' + song_id.split('|')[0]}
            else:
                return {'status': 'invalid song ID', 'error': bs_error}
    else:
        return {'status': 'invalid pool ID'}
    
def pool_unrank_cmd(song_id, pool_id):
    if pool_id in database.get_pool_ids(True):
        create_action.unrank_song(song_id, pool_id)
        return {'status': 'success'}
    else:
        return {'status': 'invalid pool ID'}
    
def pool_set_manual_cmd(song_id, pool_id, rating):
    matched_leaderboards = database.get_leaderboards([song_id])
    if not len(matched_leaderboards):
        return {'status': 'invalid song ID'}
    database.db['leaderboards'].update_one({'_id': song_id}, {'$set': {'forced_star_rating.' + pool_id: rating}})
    return {'status': 'success'}

def pool_set_automatic_cmd(song_id, pool_id):
    matched_leaderboards = database.get_leaderboards([song_id])
    if not len(matched_leaderboards):
        return {'status': 'invalid song ID'}
    database.db['leaderboards'].update_one({'_id': song_id}, {'$unset': {'forced_star_rating.' + pool_id: 1}})
    return {'status': 'success'}

def pool_set_curve_cmd(pool_id, curve_data):
    if curve_data['type'] not in curves:
        return {'status': 'invalid curve data', 'error': 'curve type does not exist'}
    if invalid_curve_data(curve_data):
        return {'status': 'invalid curve data', 'error': invalid_curve_data(curve_data)}
    database.set_pool_curve(pool_id, curve_data)
    return {'status': 'success'}
    
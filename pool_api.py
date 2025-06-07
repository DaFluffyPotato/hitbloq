from db import database
import beatsaver
import create_action

beatsaver_interface = beatsaver.BeatSaverInterface()

def create_pool_api_endpoints(app):
    pass

def valid_pool_key(request_key, pool_id):
    if pool_id in database.get_pool_ids(True):
        pool_data = database.db['ranked_lists'].find_one({'_id': pool_id})
        if pool_data['api_key'] == request_key:
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
        return {'status': 'invalid pool ID', 'error': bs_error}
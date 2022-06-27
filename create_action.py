from db import database

def create_user(scoresaber_id, queue_id=1):
    action_id = database.add_action({'type': 'add_user', 'user_id': scoresaber_id}, queue_id=queue_id)
    return action_id

def update_user(user_id, queue_id=0):
    action_id = database.add_action({'type': 'update_user', 'user_id': user_id}, queue_id=queue_id)
    return action_id

def update_users(user_ids, queue_id=2):
    action_id = database.add_action({'type': 'update_users', 'user_ids': user_ids}, queue_id=queue_id)
    return action_id

def recalculate_cr(map_pools, queue_id=2):
    action_id = database.add_action({'type': 'recalculate_cr', 'map_pools': map_pools}, queue_id=queue_id)
    return action_id

def rank_song(song_id, map_pool):
    action_id = database.add_action({'type': 'rank_song', 'song_id': song_id, 'map_pool': map_pool})
    return action_id

def unrank_song(song_id, map_pool):
    action_id = database.add_action({'type': 'unrank_song', 'song_id': song_id, 'map_pool': map_pool})
    return action_id

def update_rank_histories(map_pool, queue_id=2):
    action_id = database.add_action({'type': 'update_rank_histories', 'map_pool': map_pool}, queue_id=queue_id)
    return action_id

def regenerate_playlists():
    action_id = database.add_action({'type': 'regenerate_playlists'})
    return action_id

def refresh_profiles(queue_id=2):
    action_id = database.add_action({'type': 'refresh_profiles'}, queue_id=queue_id)
    return action_id

def refresh_pool_popularity(queue_id=2):
    action_id = database.add_action({'type': 'refresh_pool_popularity'}, queue_id=queue_id)
    return action_id

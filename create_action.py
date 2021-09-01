from db import database

def create_user(scoresaber_id):
    action_id = database.add_action({'type': 'add_user', 'user_id': scoresaber_id})
    return action_id

def update_user(user_id, priority_shift=0):
    action_id = database.add_action({'type': 'update_user', 'user_id': user_id}, priority_shift=priority_shift)
    return action_id

def update_users(user_ids):
    actions = [{'type': 'update_user', 'user_id': user_id} for user_id in user_ids]
    action_id = database.add_actions(actions)
    return action_id

def recalculate_cr(map_pools):
    action_id = database.add_action({'type': 'recalculate_cr', 'map_pools': map_pools})
    return action_id

def rank_song(song_id, map_pool):
    action_id = database.add_action({'type': 'rank_song', 'song_id': song_id, 'map_pool': map_pool})
    return action_id

def unrank_song(song_id, map_pool):
    action_id = database.add_action({'type': 'unrank_song', 'song_id': song_id, 'map_pool': map_pool})
    return action_id

def update_rank_histories(map_pool):
    action_id = database.add_action({'type': 'update_rank_histories', 'map_pool': map_pool})
    return action_id

def regenerate_playlists():
    action_id = database.add_action({'type': 'regenerate_playlists'})
    return action_id

def refresh_profiles():
    action_id = database.add_action({'type': 'refresh_profiles'})
    return action_id

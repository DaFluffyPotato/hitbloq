from db import database

def create_user(scoresaber_id):
    database.add_action({'type': 'add_user', 'user_id': scoresaber_id})

def update_user(user_id, priority_shift=0):
    database.add_action({'type': 'update_user', 'user_id': user_id}, priority_shift=priority_shift)

def update_users(user_ids):
    actions = [{'type': 'update_user', 'user_id': user_id} for user_id in user_ids]
    database.add_actions(actions)

def recalculate_cr(map_pools):
    database.add_action({'type': 'recalculate_cr', 'map_pools': map_pools})

def rank_song(song_id, map_pool):
    database.add_action({'type': 'rank_song', 'song_id': song_id, 'map_pool': map_pool})

def unrank_song(song_id, map_pool):
    database.add_action({'type': 'unrank_song', 'song_id': song_id, 'map_pool': map_pool})

def update_rank_histories(map_pool):
    database.add_action({'type': 'update_rank_histories', 'map_pool': map_pool})

def regenerate_playlists():
    database.add_action({'type': 'regenerate_playlists'})

def refresh_profiles():
    database.add_action({'type': 'refresh_profiles'})

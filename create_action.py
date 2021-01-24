from db import database

def create_user(scoresaber_id):
    database.add_action({'type': 'add_user', 'user_id': scoresaber_id})

def update_user(user_id):
    database.add_action({'type': 'update_user', 'user_id': user_id})

def update_users(user_ids):
    actions = [{'type': 'update_user', 'user_id': user_id} for user_id in user_ids]
    database.add_actions(actions)

def recalculate_cr(map_pools):
    database.add_action({'type': 'recalculate_cr', 'map_pools': map_pools})

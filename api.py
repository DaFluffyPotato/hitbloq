from flask import jsonify

from db import database

def action_list():
    resp = list(database.get_actions())
    for action in resp:
        del action['_id']
    return jsonify(resp)

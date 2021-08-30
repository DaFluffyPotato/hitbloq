import json
import time

from flask import Flask, request, make_response

from db import database
import pages
import api
from user import User
import create_action

#me = database.get_users([0])[0]
#database.update_user_cr_total(me)

app = Flask(__name__)

@app.route('/')
def home():
    return pages.home_page()

@app.route('/map_pools')
def ranked_lists():
    return pages.ranked_lists_page()

@app.route('/map_pools/<page>')
def ranked_lists_page(page):
    page = int(page)
    return pages.ranked_lists_page(page=page)

@app.route('/ranked_list/<group_id>')
def ranked_list(group_id):
    return pages.ranked_list_page(group_id)

@app.route('/ranked_list/<group_id>/<page>')
def ranked_list_page(group_id, page):
    page = int(page)
    return pages.ranked_list_page(group_id, page=page)

@app.route('/ladder/<leaderboard_id>')
def player_leaderboards(leaderboard_id):
    return pages.player_leaderboard_page(leaderboard_id, request.args.get('page'))

@app.route('/user/<int:user_id>')
def profile(user_id):
    return pages.profile_page(user_id, request.args.get('page'))

@app.route('/leaderboard/<leaderboard_id>')
def leaderboard(leaderboard_id):
    return pages.leaderboard_page(leaderboard_id, request.args.get('page'))

@app.route('/search/<search_str>')
def search(search_str):
    return pages.search_page(search_str)

@app.route('/about')
def about():
    return pages.about_page()

@app.route('/actions')
def actions_ui():
    return pages.actions_page()

@app.route('/add_user')
def add_user_page():
    return pages.add_user()

@app.route('/api/actions')
def actions():
    return api.action_list()

@app.route('/api/add_user', methods=['POST'])
def add_user():
    return api.add_user(request.json, request.remote_addr)

@app.route('/api/ranked_list/<pool_id>')
def ranked_list_api(pool_id):
    return api.ranked_list(pool_id)

@app.route('/api/ranked_list/<pool_id>/<page>')
def ranked_list_page_api(pool_id, page):
    count = 30
    page = int(page)
    return api.ranked_list(pool_id, offset=page * count)

@app.route('/api/map_pools')
def map_pools_api():
    return api.ranked_lists()

@app.route('/api/announcement')
def announcement_api():
    return api.get_announcement()

@app.route('/api/map_pools_detailed')
def map_pools_detailed_api():
    return api.get_map_pools_detailed()

@app.route('/api/leaderboard/<leaderboard_id>/info')
def leaderboard_info_api(leaderboard_id):
    return api.get_leaderboard_info(leaderboard_id)

@app.route('/api/leaderboard/<leaderboard_id>/scores')
def leaderboard_score_first_api(leaderboard_id):
    return api.get_leaderboard_scores(leaderboard_id, offset=0, count=30)

@app.route('/api/leaderboard/<leaderboard_id>/scores/<page>')
def leaderboard_scores_api(leaderboard_id, page):
    page = int(page)
    count = 30
    return api.get_leaderboard_scores(leaderboard_id, offset=page * count, count=count)

@app.route('/api/leaderboard/<leaderboard_id>/scores_extended/<page>')
def leaderboard_scores_extended_api(leaderboard_id, page):
    page = int(page)
    count = 10
    return api.get_leaderboard_scores_extended(leaderboard_id, offset=page * count, count=count)

@app.route('/api/update_user/<int:user_id>')
def update_user(user_id):
    print('received user update request for', user_id)
    last_refresh = database.db['users'].find_one({'_id': user_id})['last_manual_refresh']
    if time.time() - last_refresh > 60 * 3:
        create_action.update_user(user_id, priority_shift=60 * 60 * 24)
        database.db['users'].update_one({'_id': user_id}, {'$set': {'last_manual_refresh': time.time()}})
        return json.dumps({'time': time.time()})
    else:
        return json.dumps({'time': last_refresh})

if __name__ == "__main__":
    app.run()

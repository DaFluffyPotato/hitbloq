import json
import time

from flask import Flask, request, make_response, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from db import database
from new_pages import new_pages, get_map_pool
import api
from user import User
import create_action

app = Flask(__name__)
limiter = Limiter(
    app,
    key_func=get_remote_address,
    application_limits=['120/minute'],
    default_limits=['80/minute']
)

def api_endpoint():
    database.register_request(category='api', user_agent=request.headers.get('User-Agent'), ip=request.remote_addr, request_path=str(request.url_rule))

@app.route('/api/actions')
def actions():
    api_endpoint()
    return api.action_list()

@app.route('/api/add_user', methods=['POST'])
def add_user():
    api_endpoint()
    return api.add_user(request.json, request.remote_addr)

@app.route('/api/ranked_list/<pool_id>')
def ranked_list_api(pool_id):
    api_endpoint()
    return api.ranked_list(pool_id)

@app.route('/api/ranked_list/<pool_id>/<page>')
def ranked_list_page_api(pool_id, page):
    api_endpoint()
    count = 30
    page = int(page)
    return api.ranked_list(pool_id, offset=page * count)

@app.route('/api/ranked_list_detailed/<pool_id>/<int:page>')
def ranked_list_detailed_api(pool_id, page):
    api_endpoint()
    count = 30
    if request.args.get('per_page'):
        count = min(100, int(request.args.get('per_page')))

    return api.ranked_list_detailed(pool_id, page, count=count)

@app.route('/api/map_pools')
def map_pools_api():
    api_endpoint()
    return api.ranked_lists()

@app.route('/api/announcement')
def announcement_api():
    api_endpoint()
    return api.get_announcement()

@app.route('/api/map_pools_detailed')
def map_pools_detailed_api():
    api_endpoint()
    search = request.args.get('search') if request.args.get('search') else ''
    return api.get_map_pools_detailed(search=search)

@app.route('/api/leaderboard/<leaderboard_id>/info')
def leaderboard_info_api(leaderboard_id):
    api_endpoint()
    return api.get_leaderboard_info(leaderboard_id)

@app.route('/api/leaderboard/<leaderboard_id>/scores')
def leaderboard_score_first_api(leaderboard_id):
    api_endpoint()
    return api.get_leaderboard_scores(leaderboard_id, offset=0, count=30)

@app.route('/api/leaderboard/<leaderboard_id>/scores/<page>')
def leaderboard_scores_api(leaderboard_id, page):
    api_endpoint()
    page = int(page)
    count = 30
    return api.get_leaderboard_scores(leaderboard_id, offset=page * count, count=count)

@app.route('/api/leaderboard/<leaderboard_id>/scores_extended/<page>')
def leaderboard_scores_extended_api(leaderboard_id, page):
    api_endpoint()
    page = int(page)

    count = 10
    if request.args.get('per_page'):
        count = min(100, int(request.args.get('per_page')))

    return api.get_leaderboard_scores_extended(leaderboard_id, offset=page * count, count=count)

@app.route('/api/leaderboard/<leaderboard_id>/nearby_scores/<user>')
def laderboard_scores_nearby_api(leaderboard_id, user):
    api_endpoint()
    user = int(user)
    return api.get_leaderboard_scores_nearby(leaderboard_id, user)

@app.route('/api/leaderboard/<leaderboard_id>/nearby_scores_extended/<user>')
def laderboard_scores_nearby_extended_api(leaderboard_id, user):
    api_endpoint()
    user = int(user)
    return api.get_leaderboard_scores_nearby(leaderboard_id, user, extend=True)

@app.route('/api/leaderboard/<leaderboard_id>/friends', methods=['POST'])
def leaderboard_scores_friends_api(leaderboard_id):
    api_endpoint()
    return api.leaderboard_scores_friends(leaderboard_id, request.json['friends'])

@app.route('/api/leaderboard/<leaderboard_id>/friends_extended', methods=['POST'])
def leaderboard_scores_friends_extended_api(leaderboard_id):
    api_endpoint()
    return api.leaderboard_scores_friends(leaderboard_id, request.json['friends'], extend=True)

@app.route('/api/tools/mass_ss_to_hitbloq', methods=['POST'])
def mass_ss_to_hitbloq_id():
    api_endpoint()
    return api.mass_ss_to_hitbloq_id(request.json['ids'])

@app.route('/api/tools/ss_to_hitbloq/<ss_id>')
def ss_to_hitbloq_id(ss_id):
    api_endpoint()
    return api.ss_to_hitbloq_id(ss_id)

@app.route('/api/tools/ss_registered/<ss_id>')
def ss_registered(ss_id):
    api_endpoint()
    return api.ss_registered(ss_id)

@app.route('/api/users/<user_id>')
def user_basic_api(user_id):
    api_endpoint()
    user_id = int(user_id)
    return api.user_basic_api(user_id)

@app.route('/api/player_rank/<pool_id>/<user>')
def player_rank_api(pool_id, user):
    api_endpoint()
    user = int(user)

    # catching mod bug from versions <= 1.2.1
    if pool_id == 'None':
        return 'stop lol', 500

    return api.player_rank_api(pool_id, user)

@app.route('/api/player_ranks', methods=['POST'])
def player_ranks_api():
    api_endpoint()
    user = request.json['user']
    pool_ids = request.json['pools']
    return api.player_ranks_api(pool_ids, user)

@app.route('/api/ladder/<pool_id>/players/<int:page>')
def ranked_ladder_api(pool_id, page):
    api_endpoint()
    per_page = 10
    if request.args.get('per_page'):
        per_page = min(100, int(request.args.get('per_page')))

    search = request.args.get('search')

    return api.ranked_ladder(pool_id, page, players_per_page=per_page, search=search)

@app.route('/api/ladder/<pool_id>/nearby_players/<int:user_id>')
def ranked_ladder_nearby_api(pool_id, user_id):
    api_endpoint()
    return api.ranked_ladder_nearby(pool_id, user_id)

@app.route('/api/ladder/<pool_id>/friends', methods=['POST'])
def ranked_ladder_friends_api(pool_id):
    api_endpoint()
    return api.ranked_ladder_friends(pool_id, request.json['friends'])

@app.route('/api/user/<int:user_id>/scores')
def user_api(user_id):
    api_endpoint()
    sort_mode = 'cr'
    page = 0
    if request.args.get('sort'):
        sort_mode = request.args.get('sort')
    if request.args.get('page'):
        page = int(request.args.get('page'))
    return api.get_user_scores(user_id, get_map_pool(), sort_mode=sort_mode, page=page)

@app.route('/api/update_user/<int:user_id>')
def update_user(user_id):
    api_endpoint()
    print('received user update request for', user_id)
    last_refresh = database.db['users'].find_one({'_id': user_id})['last_manual_refresh']
    if time.time() - last_refresh > 60:
        action_id = create_action.update_user(user_id, queue_id=1)
        database.db['users'].update_one({'_id': user_id}, {'$set': {'last_manual_refresh': time.time()}})
        return json.dumps({'time': time.time(), 'id': action_id, 'error': None})
    else:
        return json.dumps({'time': last_refresh, 'id': None, 'error': 'refreshed too quickly'})

@app.route('/api/action_status/<action_id>')
def action_id_status(action_id):
    api_endpoint()
    return api.action_id_status(action_id)

@app.route('/api/queue_statuses')
def action_queue_statuses():
    api_endpoint()
    return api.action_queue_statuses()

@app.route('/api/get_template/<template_id>')
def get_template(template_id):
    api_endpoint()
    return api.get_template(template_id)

@app.route('/api/event')
def get_current_event():
    api_endpoint()
    return api.get_current_event()

@app.route('/api/popular_pools')
def get_popular_pools():
    api_endpoint()
    popular_pool_threshold = 15
    return api.get_popular_pools(popular_pool_threshold)

@app.route('/api/player_badges/<int:user_id>')
def get_player_badges(user_id):
    api_endpoint()
    return api.get_player_badges(user_id)

@app.route('/api/pool_feed/<pool_id>')
def get_pool_feed(pool_id):
    api_endpoint()
    page = 0
    if request.args.get('page'):
        page = int(request.args.get('page'))
    return api.pool_feed(pool_id, page)

@app.route('/api/mm/ss_user/<scoresaber_id>')
def get_mm_ss_user(scoresaber_id):
    api_endpoint()
    return jsonify(api.mm.profile(scoresaber_id))

@app.route('/api/mm/user/<int:user_id>')
def get_mm_user(user_id):
    api_endpoint()
    return jsonify(api.mm.profile(user_id))

@app.route('/api/mm/active_pools')
def get_mm_pools():
    api_endpoint()
    return jsonify(api.mm.pools())

@app.route('/api/mm/submit_match', methods=['POST'])
def submit_mm_match():
    api_endpoint()
    return jsonify(api.mm.submit_match(request.json))

@app.route('/')
def new_home():
    html = new_pages['home']()
    return html

@app.route('/about')
def new_about():
    html = new_pages['about']()
    return html

@app.route('/map_pools')
def new_map_pools():
    html = new_pages['map_pools']()
    return html

@app.route('/map_pool/<pool_id>')
def new_map_pool(pool_id):
    html = new_pages['map_pool'](pool_id)
    return html

@app.route('/ladder/<ladder>')
def new_ladder(ladder):
    html = new_pages['ladder'](ladder)
    return html

@app.route('/leaderboard/<leaderboard_id>')
def new_leaderboard(leaderboard_id):
    html = new_pages['leaderboard'](leaderboard_id)
    return html

@app.route('/user/<int:user_id>')
def new_user(user_id):
    html = new_pages['user'](user_id)
    return html

@app.route('/ranked_list/<pool_id>')
def new_ranked_list(pool_id):
    html = new_pages['ranked_list'](pool_id)
    return html

@app.route('/add_user')
def new_add_user():
    html = new_pages['add_user']()
    return html

@app.route('/actions')
def new_actions():
    html = new_pages['actions']()
    return html

@app.route('/contact')
def contact():
    html = new_pages['contact']()
    return html

@app.route('/discord')
def discord():
    html = new_pages['discord']()
    return html

@app.after_request
def after_request(response):
    if request.path.split('.')[-1] == 'bplist':
        response.headers['Cache-Control'] = 'no-store'
    return response

if __name__ == "__main__":
    app.run()

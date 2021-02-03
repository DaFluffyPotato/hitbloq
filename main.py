from flask import Flask, request, make_response

from db import database
import pages
import api
from user import User

#me = database.get_users([0])[0]
#database.update_user_cr_total(me)

app = Flask(__name__)

@app.route('/')
def home():
    return pages.home_page()

@app.route('/map_pools')
def ranked_lists():
    return pages.ranked_lists_page()

@app.route('/ranked_list/<group_id>')
def ranked_list(group_id):
    return pages.ranked_list_page(group_id)

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

@app.route('/api/announcement')
def announcement_api():
    return api.get_announcement()

if __name__ == "__main__":
    app.run()

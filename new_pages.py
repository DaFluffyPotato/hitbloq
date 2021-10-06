from flask import request

from templates import templates
from db import database
from profile import Profile
from pages import get_map_pool
from general import epoch_to_date

new_pages = {}

def page(page_func):
    new_pages[page_func.__name__] = page_func

def generate_header(title='Hitbloq', desc='a competitive beat saber service', image='https://hitbloq.com/static/hitbloq.png', additional_css=[], additional_js=[]):
    header = '<title>' + title + '</title>\n'
    header += '<link rel="icon" href="https://hitbloq.com/static/hitbloq.png">\n'
    header += '<meta property="og:image" content="' + image + '">\n'
    header += '<meta property="og:image:secure_url" content="' + image + '">\n'
    header += '<meta property="og:title" content="' + title + '">\n'
    header += '<meta property="og:description" content="' + desc + '">\n'
    header += '<meta property="og:type" content="website">\n'
    header += '<meta property="og:url" content="' + request.path + '">\n'
    header += '<meta property="og:site_name" content="Hitbloq">\n'
    for css_file in additional_css:
        header += '<link rel="stylesheet" href="/static/css/' + css_file + '">\n'
    for js_file in additional_js:
        header += '<script src="/static/js/' + js_file + '"></script>\n'
    return header

def page_setup():
    setup_data = {}
    return setup_data

@page
def home():
    header = generate_header(additional_css=['new_home.css'])
    setup_data = page_setup()
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_home', {})})
    return html

@page
def about():
    header = generate_header(additional_css=['new_about.css'])
    setup_data = page_setup()
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_about', {})})
    return html

@page
def map_pools():
    header = generate_header(additional_css=['new_map_pools.css'], additional_js=['new_map_pools.js'])
    setup_data = page_setup()
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_map_pools', {})})
    return html

@page
def ladder(ladder_id):
    header = generate_header(additional_css=['new_player_leaderboard.css'], additional_js=['new_player_leaderboard.js'])
    setup_data = page_setup()

    shown_name = database.db['ranked_lists'].find_one({'_id': ladder_id})['shown_name']

    next_page = int(request.args.get('page')) + 1 if request.args.get('page') else 1
    last_page = max(int(request.args.get('page')) - 1, 0) if request.args.get('page') else 0
    next_page = request.path + '?page=' + str(next_page)
    last_page = request.path + '?page=' + str(last_page)

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_player_leaderboard', {'shown_name': shown_name, 'page_right': next_page, 'page_left': last_page})})
    return html

@page
def user(user_id):
    header = generate_header(additional_css=['new_player_profile.css'], additional_js=['new_player_profile.js'])
    setup_data = page_setup()

    next_page = int(request.args.get('page')) + 1 if request.args.get('page') else 1
    last_page = max(int(request.args.get('page')) - 1, 0) if request.args.get('page') else 0
    next_page = request.path + '?page=' + str(next_page)
    last_page = request.path + '?page=' + str(last_page)

    sort_mode = request.args.get('sort')

    pool_id = get_map_pool()

    profile_obj = Profile(user_id)
    pool_data = profile_obj.user.generate_rank_info(database, pool_id)

    profile_insert = {
        'username': profile_obj.user.username,
        'pfp': profile_obj.user.profile_pic,
        'joined': epoch_to_date(profile_obj.user.date_created),
        'total_scores': '{:,}'.format(profile_obj.user.scores_total),
        'pool_scores_set': '{:,}'.format(len(profile_obj.user.scores)),
        'rank_img': '/static/ranks/default/' + profile_obj.user.pool_tier + '.png',
        'pool_rank': '{:,}'.format(profile_obj.user.pool_rank),
        'pool_max_rank': '{:,}'.format(profile_obj.user.pool_max_rank),
        'pool_cr': '{:,}'.format(round(profile_obj.user.pool_cr_total, 2)),
        'selected_pool': pool_data['shown_name'],
    }

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_player_profile', profile_insert)})
    return html

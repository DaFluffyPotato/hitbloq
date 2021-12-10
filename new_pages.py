from flask import request

from templates import templates
from db import database
from profile import Profile
from general import epoch_to_date, lengthen_settings
import urllib.parse

new_pages = {}

def get_map_pool():
    user_ip = request.remote_addr
    map_pool = request.cookies.get('map_pool')
    # a temp hack to get around people with global_main as their cached pool
    if (not map_pool) or (map_pool == 'global_main'):
        map_pool = 'bbbear'
    else:
        database.log_interest(user_ip, map_pool)
    if request.args.get('pool'):
        map_pool = request.args.get('pool')
    return map_pool

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
    database.inc_counter('views')
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

    sort_mode = request.args.get('sort')

    pool_id = get_map_pool()

    next_page = request.path + '?page=' + str(next_page) + '&pool=' + pool_id
    last_page = request.path + '?page=' + str(last_page) + '&pool=' + pool_id
    if sort_mode:
        next_page += '&sort=' + sort_mode
        last_page += '&sort=' + sort_mode
    sort_change_url = request.path + '?pool=' + pool_id + '&sort=sort_replace'

    profile_obj = Profile(user_id)
    pool_data = profile_obj.user.generate_rank_info(database, pool_id)

    if profile_obj.user.profile_banner:
        banner_style = 'background: linear-gradient(to right, rgba(0, 0, 0, 0.25) 0%, rgba(0, 0, 0, 0.25) 100%), url(' + profile_obj.user.profile_banner + '); background-size: cover;'
    else:
        banner_style = ''

    if profile_obj.user.profile_background:
        background_style = 'background: linear-gradient(to right, rgba(0, 0, 0, 0.25) 0%, rgba(0, 0, 0, 0.25) 100%), url(' + profile_obj.user.profile_background + '); background-size: cover;'
    else:
        background_style = ''

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
        'page_left': last_page,
        'page_right': next_page,
        'sort_newest': sort_change_url.replace('sort_replace', 'newest'),
        'sort_cr': sort_change_url.replace('sort_replace', 'cr'),
        'sort_oldest': sort_change_url.replace('sort_replace', 'oldest'),
        'player_banner_styling': banner_style,
        'last_manual_refresh': str(profile_obj.user.last_manual_refresh),
    }

    html = templates.inject('new_base', {'header': header, 'cont_styling': background_style, 'content': templates.inject('new_player_profile', profile_insert)})
    return html

@page
def leaderboard(leaderboard_id):
    header = generate_header(additional_css=['new_leaderboard.css'], additional_js=['new_leaderboard.js'])
    setup_data = page_setup()

    pool_id = get_map_pool()
    try:
        shown_name = database.db['ranked_lists'].find_one({'_id': pool_id})['shown_name']
    except:
        shown_name = None

    next_page = int(request.args.get('page')) + 1 if request.args.get('page') else 1
    last_page = max(int(request.args.get('page')) - 1, 0) if request.args.get('page') else 0
    next_page = request.path + '?page=' + str(next_page) + '&pool=' + pool_id
    last_page = request.path + '?page=' + str(last_page) + '&pool=' + pool_id

    try:
        leaderboard_data = database.search_leaderboards({'key': leaderboard_id.split('_')[0], 'difficulty_settings': lengthen_settings('_'.join(leaderboard_id.split('_')[1:]))})[0]
    except IndexError:
        leaderboard_data = database.search_leaderboards({'hash': leaderboard_id.split('_')[0], 'difficulty_settings': lengthen_settings('_'.join(leaderboard_id.split('_')[1:]))})[0]

    star_rating = 0
    if pool_id in leaderboard_data['star_rating']:
        star_rating = leaderboard_data['star_rating'][pool_id]

    leaderboard_insert = {
        'leaderboard_info_styling': 'background-image: url(' + leaderboard_data['cover'] + '); -webkit-filter: blur(2px);',
        'cover': leaderboard_data['cover'],
        'name': leaderboard_data['name'],
        'artist': leaderboard_data['artist'],
        'mapper': leaderboard_data['mapper'],
        'difficulty': leaderboard_data['difficulty'],
        'stars': str(star_rating) + '★ ' + (('(' + shown_name + ')') if shown_name else ''),
        'nps': str(round(leaderboard_data['notes'] / leaderboard_data['duration'], 2)) if leaderboard_data['duration'] else 'missing ',
        'key': leaderboard_data['key'],
        'hash': leaderboard_data['hash'],
        'page_left': last_page,
        'page_right': next_page,
    }

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_leaderboard', leaderboard_insert)})
    return html

@page
def ranked_list(pool_id):
    header = generate_header(additional_css=['new_ranked_list.css'], additional_js=['new_ranked_list.js'])
    setup_data = page_setup()

    database.log_interest(request.remote_addr, pool_id)

    pool_id = request.path.split('/')[-1]
    pool_data = database.db['ranked_lists'].find_one({'_id': pool_id})

    next_page = int(request.args.get('page')) + 1 if request.args.get('page') else 1
    last_page = max(int(request.args.get('page')) - 1, 0) if request.args.get('page') else 0
    next_page = request.path + '?page=' + str(next_page)
    last_page = request.path + '?page=' + str(last_page)

    ranked_list_insert = {
        'shown_name': pool_data['shown_name'],
        'page_left': last_page,
        'page_right': next_page,
    }

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_ranked_list', ranked_list_insert)})
    return html

@page
def add_user():
    header = generate_header(additional_css=['new_add_user.css'], additional_js=['new_add_user.js'])
    setup_data = page_setup()

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_add_user', {})})
    return html

@page
def actions():
    header = generate_header(additional_css=['new_actions.css'], additional_js=['new_actions.js'])
    setup_data = page_setup()

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_actions', {})})
    return html

@page
def map_pool(pool_id):
    pool_data = database.db['ranked_lists'].find_one({'_id': pool_id})

    header = generate_header(
        additional_css=['new_map_pools.css', 'new_map_pool.css'],
        additional_js=['new_map_pool.js'],
        image='https://hitbloq.com/static/hitbloq.png' if not pool_data['playlist_cover'] else pool_data['playlist_cover'],
        title='Hitbloq - ' + pool_data['shown_name'] + ' Map Pool',
        desc='The ' + pool_data['shown_name'] + ' map pool.' if not pool_data['short_description'] else pool_data['short_description']
    )

    setup_data = page_setup()

    download_url = '/static/hashlists/' + pool_id + '.bplist'

    owner_discord_accounts = {user['_id'] : user['tag'] for user in database.get_discord_users(pool_data['owners'])}
    owner_text = ''
    for owner in pool_data['owners']:
        if owner_text != '':
             owner_text += '<br>'
        if owner in owner_discord_accounts:
            owner_text += owner_discord_accounts[owner]
        else:
            owner_text += str(owner) + ' (ID)'

    inject_data = {
        'shown_name': pool_data['shown_name'],
        'download_url': download_url,
        'pool_id': pool_id,
        'pool_description': pool_data['long_description'],
        'owners': owner_text,
    }

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_map_pool', inject_data)})
    return html

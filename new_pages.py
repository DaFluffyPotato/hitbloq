import json
import time

from flask import request

from templates import templates
from db import database
from profile import Profile
from general import epoch_to_date, lengthen_settings, format_num
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
    resolve_pool_id(map_pool)
    return map_pool

def resolve_pool_id(pool_id):
    pool_reference = database.db['pool_preferences'].find_one({'_id': pool_id})
    if pool_reference:
        return pool_reference['target']
    return pool_id

def page(page_func):
    new_pages[page_func.__name__] = page_func

def generate_header(title='Hitbloq', desc='a competitive beat saber service', image='https://hitbloq.com/static/hitbloq.png', additional_css=[], additional_js=[]):
    header = '<title>' + title + '</title>\n'
    header += '<link rel="icon" href="https://hitbloq.com/static/hitbloq.png">\n'
    header += '<meta name="theme-color" content="#2ce8f5">'
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
    database.register_request(category='website', user_agent=request.headers.get('User-Agent'), ip=request.remote_addr)
    return setup_data

@page
def home():
    header = generate_header(additional_css=['new_home.css'])
    setup_data = page_setup()
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_home', {})})
    return html

@page
def about():
    header = generate_header(title='About Hitbloq', additional_css=['new_about.css'])
    setup_data = page_setup()
    about_stats = {
        'website_views': format_num(int(database.get_counter('views')['count'])),
        'api_requests': format_num(int(database.get_counter('api_reqs')['count'])),
        'users': format_num(int(database.db['users'].find({}).count())),
        'scores': format_num(int(database.db['scores'].find({}).count())),
        'leaderboards': format_num(int(database.db['leaderboards'].find({}).count())),
        'pools': format_num(int(database.db['ranked_lists'].find({}).count())),
        'new_users': format_num(int(database.db['users'].find({'date_created': {'$gt': time.time() - (60 * 60 * 24)}}).count())),
    }
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_about', about_stats)})
    return html

@page
def map_pools():
    header = generate_header(title='Map Pools', desc='Hitbloq Map Pools', additional_css=['new_map_pools.css'], additional_js=['new_map_pools.js'])
    setup_data = page_setup()
    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_map_pools', {})})
    return html

@page
def ladder(ladder_id):
    shown_name = database.db['ranked_lists'].find_one({'_id': ladder_id})['shown_name']

    header = generate_header(
        title=shown_name + ' Ladder',
        desc='The competitive ladder for the ' + shown_name + ' map pool.',
        additional_css=['new_player_leaderboard.css'],
        additional_js=['new_player_leaderboard.js']
    )
    setup_data = page_setup()

    next_page = int(request.args.get('page')) + 1 if request.args.get('page') else 1
    last_page = max(int(request.args.get('page')) - 1, 0) if request.args.get('page') else 0
    next_page = request.path + '?page=' + str(next_page)
    last_page = request.path + '?page=' + str(last_page)

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_player_leaderboard', {'shown_name': shown_name, 'page_right': next_page, 'page_left': last_page})})
    return html

@page
def user(user_id):
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
        'pool_rank': '<a href="/ladder/' + pool_id + '?page=' + str(int((profile_obj.user.pool_rank - 1) / 50)) + '" class="link">#' + '{:,}'.format(profile_obj.user.pool_rank) + '</a>',
        'pool_max_rank': '#' + '{:,}'.format(profile_obj.user.pool_max_rank),
        'pool_cr': '{:,}'.format(round(profile_obj.user.pool_cr_total, 2)),
        'selected_pool': pool_data['shown_name'],
        'page_left': last_page,
        'page_right': next_page,
        'sort_newest': sort_change_url.replace('sort_replace', 'newest'),
        'sort_cr': sort_change_url.replace('sort_replace', 'cr'),
        'sort_oldest': sort_change_url.replace('sort_replace', 'oldest'),
        'player_banner_styling': banner_style,
        'last_manual_refresh': str(profile_obj.user.last_manual_refresh),
        'scoresaber_id': profile_obj.user.scoresaber_id,
    }

    desc_text = 'Rank: #' + '{:,}'.format(profile_obj.user.pool_rank) + '\n'
    desc_text += 'Tier: ' + profile_obj.user.pool_tier + '\n'
    desc_text += 'Competitive Rating: ' + '{:,}'.format(round(profile_obj.user.pool_cr_total, 2)) + 'cr\n'
    desc_text += 'Scores Set: ' + '{:,}'.format(len(profile_obj.user.scores))

    header = generate_header(
        additional_css=['new_player_profile.css'],
        additional_js=['new_player_profile.js'],
        title=profile_obj.user.username + '\'s Profile - ' + pool_data['shown_name'],
        image=profile_obj.user.profile_pic,
        desc=desc_text
    )
    setup_data = page_setup()

    html = templates.inject('new_base', {'header': header, 'cont_styling': background_style, 'content': templates.inject('new_player_profile', profile_insert)})
    return html

@page
def leaderboard(leaderboard_id):
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

    desc_text = 'Artist: ' + leaderboard_data['artist'] + '\n'
    desc_text += 'Mapper: ' + leaderboard_data['mapper'] + '\n'
    desc_text += 'Difficulty: ' + leaderboard_data['difficulty'] + '\n'
    desc_text += 'Stars: ' + leaderboard_insert['stars']

    header = generate_header(
        title=leaderboard_data['name'],
        image=leaderboard_data['cover'],
        desc=desc_text,
        additional_css=['new_leaderboard.css'],
        additional_js=['new_leaderboard.js']
    )
    setup_data = page_setup()

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_leaderboard', leaderboard_insert)})
    return html

@page
def ranked_list(pool_id):
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

    header = generate_header(
        title=pool_data['shown_name'] + ' Ranked List',
        desc='The list of ranked maps in the ' + pool_data['shown_name'] + ' map pool.',
        additional_css=['new_ranked_list.css'],
        additional_js=['new_ranked_list.js']
    )
    setup_data = page_setup()

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
    
    database.log_interest(request.remote_addr, pool_id)

    pool_data = database.db['ranked_lists'].find_one({'_id': pool_id})

    header = generate_header(
        additional_css=['new_map_pools.css', 'new_map_pool.css'],
        additional_js=['new_map_pool.js'],
        image='https://hitbloq.com/static/hitbloq.png' if not pool_data['playlist_cover'] else pool_data['playlist_cover'],
        title=pool_data['shown_name'] + ' Map Pool',
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
        'creation_date': epoch_to_date(pool_data['date_created']),
        'popularity': '{:,}'.format(int(pool_data['priority'])),
        'views': '{:,}'.format(int(pool_data['views'])),
        'ranked_maps': '{:,}'.format(len(pool_data['leaderboard_id_list'])),
        'accumulation_constant': str(pool_data['accumulation_constant']),
        'curve_data': json.dumps(pool_data['cr_curve']),
    }

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_map_pool', inject_data)})
    return html

@page
def contact():
    header = generate_header(
        image='https://hitbloq.com/static/hitbloq.png',
        title='Contact',
        desc='Contact Hitbloq at hitbloqbs@gmail.com'
    )
    setup_data = page_setup()

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_contact', {})})
    return html

@page
def discord():
    header = generate_header(
        image='https://hitbloq.com/static/hitbloq.png',
        title='Discord',
        desc='Join the Hitbloq Discord!'
    )
    setup_data = page_setup()

    html = templates.inject('new_base', {'header': header, 'content': templates.inject('new_discord', {})})
    return html

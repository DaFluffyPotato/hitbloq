from flask import request

from db import database
from profile import Profile
from templates import templates
from user import User
from general import shorten_settings, lengthen_settings, max_score
from cr_formulas import *

def generate_header(image, title, description):
    header = '<title>' + title + '</title>\n'
    header += '<link rel="icon" href="https://hitbloq.com/static/hitbloq.png">\n'
    header += '<meta property="og:image" content="' + image + '">\n'
    header += '<meta property="og:image:secure_url" content="' + image + '">\n'
    header += '<meta property="og:title" content="' + title + '">\n'
    header += '<meta property="og:description" content="' + description + '">\n'
    header += '<meta property="og:type" content="website">\n'
    header += '<meta property="og:url" content="' + request.path + '">\n'
    header += '<meta property="og:site_name" content="Hitbloq">\n'
    return header

def get_map_pool():
    map_pool = request.cookies.get('map_pool')
    if not map_pool:
        map_pool = 'global_main'
    if request.args.get('pool'):
        map_pool = request.args.get('pool')
    return map_pool

def normal_page(contents, title='Hitbloq', desc='a competitive beat saber service', image='https://hitbloq.com/static/hitbloq.png'):
    if title != 'Hitbloq':
        title = 'Hitbloq - ' + title

    map_pool = get_map_pool()

    page_html = templates.inject('layout', {'page_content': contents, 'map_pool': map_pool, 'page_header': generate_header(image, title, desc)})
    return page_html

def home_page():
    home_content = '<h2>Active Development Zone!!!</h2>Hitbloq\'s third iteration is being developed. Some whacky stuff happened in the past when we tried to switch to using our own mod, which resulted in the previous two iterations getting killed off.<br>For the time being, you can <a href="/user/0">look around</a> or check out <a href="/about">About</a>.<br><br>You can track my progress in the <a href="https://github.com/DaFluffyPotato/hitbloq">GitHub Repo</a>.'
    home_html = normal_page(templates.inject('simple_card_layout', {'page_content': home_content}))
    return home_html

def actions_page():
    actions_html = normal_page(templates.inject('actions_layout', {}), 'Action Queue', 'action queue')
    return actions_html

def add_user():
    add_user_html = normal_page(templates.inject('add_user_layout', {}), 'Add User', 'add a user to Hitbloq')
    return add_user_html

def search_page(search_str):
    search_html = normal_page(templates.inject('search_results_layout', {'search_results': generate_search_entries(search_str)}), search_str + ' Search Results', 'player search results for ' + search_str)
    return search_html

def generate_search_entries(search_str):
    player_limit = 50
    search_leaderboard_entries_html = ''

    map_pool = get_map_pool()

    users = [User().load(user) for user in list(database.db['users'].find({'username': {'$regex': search_str, '$options': 'i'}}).sort('total_cr.' + map_pool, -1).limit(50))]

    for user in users:
        values = {
            'profile_picture': user.profile_pic,
            'user_name': '<a href="/user/' + str(user.id) + '">' + user.username + '</a>',
            'user_cr': str(round(user.cr_totals[map_pool], 2)),
        }
        search_leaderboard_entries_html += templates.inject('search_leaderboard_entry', values)

    return search_leaderboard_entries_html

def player_leaderboard_page(map_pool, page):
    page = 0 if (page == None) else int(page)

    map_pool = database.get_ranked_list(map_pool)

    values = {
        'map_pool_name': map_pool['shown_name'],
        'leaderboard_scores': generate_player_leaderboard_entries(map_pool, page),
        'next_page': request.path.split('?')[0] + '?page=' + str(page + 1),
        'last_page': request.path.split('?')[0] + '?page=' + str(max(page - 1, 0)),
    }

    leaderboards_html = normal_page(templates.inject('player_leaderboard_layout', values), map_pool['shown_name'] + ' Leaderboard', 'player leaderboard for the ' + map_pool['shown_name'] + ' map pool')
    return leaderboards_html

def generate_player_leaderboard_entries(map_pool, page):
    players_per_page = 50
    player_leaderboard_entries_html = ''

    ladder_data = database.get_ranking_slice(map_pool['_id'], page * players_per_page, (page + 1) * players_per_page)
    user_id_list = [user['user'] for user in ladder_data['ladder']]
    user_map = {user.id : user for user in database.get_users(user_id_list)}
    for i, user in enumerate(user_id_list):
        values = {
            'profile_picture': user_map[user].profile_pic,
            'user_rank': str(page * players_per_page + i + 1),
            'user_name': '<a href="/user/' + str(user) + '">' + user_map[user].username + '</a>',
            'user_cr': str(round(user_map[user].cr_totals[map_pool['_id']], 2)),
        }
        player_leaderboard_entries_html += templates.inject('player_leaderboard_entry', values)

    return player_leaderboard_entries_html


def ranked_lists_page():
    ranked_list_entry_html = ''
    map_pool = get_map_pool()

    for ranked_list in database.get_ranked_lists():
        if not ranked_list['third_party']:
            select_status = 'select'
            if map_pool == ranked_list['_id']:
                select_status = 'selected'
            values = {
                'entry_link': '/ranked_list/' + ranked_list['_id'],
                'entry_img': ranked_list['cover'],
                'entry_title': ranked_list['shown_name'],
                'select_status': select_status,
                'map_pool_id': ranked_list['_id'],
            }
            ranked_list_entry_html += templates.inject('ranked_list_entry_layout', values)
    ranked_lists_html = normal_page(templates.inject('ranked_lists_layout', {'ranked_lists': ranked_list_entry_html}), 'Map Pools', 'map pools')
    return ranked_lists_html

def ranked_list_page(group_id):
    ranked_list_data = database.get_ranked_list(group_id)
    leaderboard_list = database.get_leaderboards(ranked_list_data['leaderboard_id_list'])

    # fix missing values for lambda search
    for leaderboard in leaderboard_list:
        if group_id not in leaderboard['star_rating']:
            leaderboard['star_rating'][group_id] = 0

    leaderboard_list.sort(key=lambda x: x['star_rating'][group_id], reverse=True)
    ranked_songs_html = ''
    for leaderboard in leaderboard_list:
        star_rating = 0
        if group_id in leaderboard['star_rating']:
            star_rating = leaderboard['star_rating'][group_id]
        values = {
            'song_img': 'https://beatsaver.com' + leaderboard['cover'],
            'song_name': '<a href="/leaderboard/' + leaderboard['key'] + '_' + shorten_settings(leaderboard['difficulty_settings']) + '">' + leaderboard['name'] + '</a>',
            'song_plays': str(len(leaderboard['score_ids'])),
            'song_difficulty': str(star_rating) + '★',
        }
        ranked_songs_html += templates.inject('ranked_song_entry', values)
    ranked_list_html = normal_page(templates.inject('ranked_list_layout', {'table_entries': ranked_songs_html}), group_id + ' Ranked List', 'all ranked songs for the ' + group_id + ' map pool')
    return ranked_list_html

def about_page():
    about_html = normal_page(templates.inject('about_layout', {}))
    return about_html

def leaderboard_page(leaderboard_id, page):
    if page == None:
        page = 0
    else:
        page = int(page)

    map_pool = get_map_pool()

    leaderboard_data = database.search_leaderboards({'key': leaderboard_id.split('_')[0], 'difficulty_settings': lengthen_settings('_'.join(leaderboard_id.split('_')[1:]))})[0]
    star_rating = 0
    if map_pool in leaderboard_data['star_rating']:
        star_rating = leaderboard_data['star_rating'][map_pool]
    leaderboard_insert = {
        'leaderboard_scores': generate_leaderboard_entries(leaderboard_data, page),
        'song_name': leaderboard_data['name'],
        'artist_name': leaderboard_data['artist'],
        'mapper_name': leaderboard_data['mapper'],
        'song_difficulty': leaderboard_data['difficulty'],
        'star_rating': str(star_rating) + '★',
        'notes_per_second': str(round(leaderboard_data['notes'] / leaderboard_data['length'], 2)),
        'pulse_rate': str(1 / leaderboard_data['bpm'] * 60 * 2) + 's',
        'song_picture': 'https://beatsaver.com' + leaderboard_data['cover'],
        'beatsaver_id': leaderboard_data['key'],
        'next_page': request.path.split('?')[0] + '?page=' + str(page + 1),
        'last_page': request.path.split('?')[0] + '?page=' + str(max(page - 1, 0)),
    }
    leaderboard_html = normal_page(templates.inject('leaderboard_layout', leaderboard_insert), leaderboard_data['name'] + ' Leaderboard', 'song leaderboard for ' + leaderboard_data['name'], 'https://beatsaver.com' + leaderboard_data['cover'])
    return leaderboard_html

def generate_leaderboard_entries(leaderboard_data, page):
    page_length = 25
    html = ''

    visible_scores = list(database.fetch_scores(leaderboard_data['score_ids']).sort('score', -1))[page_length * page : page_length * (page + 1)]
    user_ids = [score['user'] for score in visible_scores]
    score_users = database.get_users(user_ids)

    # use a hash map for quick assignment
    score_dict = {}
    for score in visible_scores:
        score_dict[score['user']] = score
    for user in score_users:
        score_dict[user.id]['user_obj'] = user

    map_pool = get_map_pool()

    # generate html
    for i, score in enumerate(visible_scores):
        cr_given = 0
        if map_pool in score['cr']:
            cr_given = score['cr'][map_pool]

        entry_values = {
            'profile_picture': score['user_obj'].profile_pic,
            'score_rank': str(page_length * page + i + 1),
            'score_name': '<a href="/user/' + str(score['user']) + '">' + score['user_obj'].username + '</a>',
            'score_accuracy': str(round(score['score'] / max_score(leaderboard_data['notes']) * 100, 2)),
            'score_cr': str(round(cr_given, 2)),
        }
        html += templates.inject('leaderboard_entry', entry_values)

    return html

def profile_page(user_id, profile_page):
    # TODO: switch mongo requests to async
    if profile_page == None:
        profile_page = 0
    else:
        profile_page = int(profile_page)

    map_pool = get_map_pool()

    profile_obj = Profile(user_id)
    profile_obj.user.load_pool_scores(database, map_pool)

    player_cr_total = 0
    if map_pool in profile_obj.user.cr_totals:
        player_cr_total = profile_obj.user.cr_totals[map_pool]

    player_rank = database.get_user_ranking(profile_obj.user, map_pool)

    profile_insert = {}
    profile_insert.update(profile_obj.insert_info)
    profile_insert.update({
        'played_songs': generate_profile_entries(profile_obj, profile_page),
        'player_rank': str(player_rank),
        'player_cr': str(round(player_cr_total, 2)),
        'next_page': request.path.split('?')[0] + '?page=' + str(profile_page + 1),
        'last_page': request.path.split('?')[0] + '?page=' + str(max(profile_page - 1, 0)),
    })
    profile_html = normal_page(templates.inject('profile_layout', profile_insert), profile_obj.user.username + '\'s Profile', profile_obj.user.username + '\'s Hitbloq profile', profile_obj.user.profile_pic)
    return profile_html

def generate_profile_entries(profile_obj, profile_page):
    page_length = 10
    html = ''

    map_pool = get_map_pool()

    profile_obj.user.scores.sort(key=lambda x : x['cr'][map_pool], reverse=True)
    visible_scores = profile_obj.user.scores[profile_page * page_length : (profile_page + 1) * page_length]

    profile_obj.fetch_score_leaderboards(visible_scores)
    for i, score in enumerate(visible_scores):
        inject_values = {
            'song_rank': str(score['rank']),
            'song_name': '<a href="/leaderboard/' + score['leaderboard']['key'] + '_' + shorten_settings(score['song_id'].split('|')[1]) + '">' + score['leaderboard']['name'] + '</a>',
            'cr_received': str(round(score['cr'][map_pool], 2)),
            'weighted_cr': str(round(score['cr'][map_pool] * cr_accumulation_curve(i + profile_page * page_length), 2)),
            'accuracy': str(score['accuracy']),
            'song_pic': 'https://beatsaver.com' + score['leaderboard']['cover'],
        }
        html += templates.inject('profile_entry_layout', inject_values)
    return html

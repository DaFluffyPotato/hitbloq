from flask import request

from db import database
from profile import Profile
from templates import templates
from general import shorten_settings, lengthen_settings, max_score

def home_page():
    home_content = '<h2>Active Development Zone!!!</h2>Hitbloq\'s third iteration is being developed. Some whacky stuff happened in the past when we tried to switch to using our own mod, which resulted in the previous two iterations getting killed off.<br>For the time being, you can <a href="/user/0">look around</a> or check out <a href="/about">About</a>.<br><br>You can track my progress in the <a href="https://github.com/DaFluffyPotato/hitbloq">GitHub Repo</a>.'
    home_html = templates.inject('layout', {'page_content': templates.inject('simple_card_layout', {'page_content': home_content})})
    return home_html

def leaderboards_page():
    leaderboards_html = templates.inject('layout', {'page_content': templates.inject('simple_card_layout', {'page_content': 'coming soon...'})})
    return leaderboards_html

def ranked_lists_page():
    ranked_list_entry_html = ''
    for ranked_list in database.get_ranked_lists():
        if not ranked_list['third_party']:
            values = {
                'entry_link': '/ranked_list/' + ranked_list['_id'],
                'entry_img': ranked_list['cover'],
                'entry_title': ranked_list['shown_name'],
            }
            ranked_list_entry_html += templates.inject('ranked_list_entry_layout', values)
    ranked_lists_html = templates.inject('layout', {'page_content': templates.inject('ranked_lists_layout', {'ranked_lists': ranked_list_entry_html})})
    return ranked_lists_html

def ranked_list_page(group_id):
    ranked_list_data = database.get_ranked_list(group_id)
    leaderboard_list = database.get_leaderboards(ranked_list_data['leaderboard_id_list'])
    ranked_songs_html = ''
    for leaderboard in leaderboard_list:
        values = {
            'song_img': 'https://beatsaver.com' + leaderboard['cover'],
            'song_name': '<a href="/leaderboard/' + leaderboard['key'] + '_' + shorten_settings(leaderboard['difficulty_settings']) + '">' + leaderboard['name'] + '</a>',
            'song_plays': str(len(leaderboard['score_ids'])),
            'song_difficulty': str(0.0) + '★',
        }
        ranked_songs_html += templates.inject('ranked_song_entry', values)
    ranked_list_html = templates.inject('layout', {'page_content': templates.inject('ranked_list_layout', {'table_entries': ranked_songs_html})})
    return ranked_list_html

def about_page():
    about_html = templates.inject('layout', {'page_content': templates.inject('about_layout', {})})
    return about_html

def leaderboard_page(leaderboard_id, leaderboard_page):
    if leaderboard_page == None:
        leaderboard_page = 0
    else:
        leaderboard_page = int(leaderboard_page)

    leaderboard_data = database.search_leaderboards({'key': leaderboard_id.split('_')[0], 'difficulty_settings': lengthen_settings('_'.join(leaderboard_id.split('_')[1:]))})[0]
    leaderboard_insert = {
        'leaderboard_scores': generate_leaderboard_entries(leaderboard_data, leaderboard_page),
        'song_name': leaderboard_data['name'],
        'artist_name': leaderboard_data['artist'],
        'mapper_name': leaderboard_data['mapper'],
        'song_difficulty': leaderboard_data['difficulty'],
        'star_rating': str(0.0) + '★',
        'notes_per_second': str(round(leaderboard_data['notes'] / leaderboard_data['length'], 2)),
        'pulse_rate': str(1 / leaderboard_data['bpm'] * 60 * 2) + 's',
        'song_picture': 'https://beatsaver.com' + leaderboard_data['cover'],
        'beatsaver_id': leaderboard_data['key'],
        'next_page': request.path.split('?')[0] + '?page=' + str(leaderboard_page + 1),
        'last_page': request.path.split('?')[0] + '?page=' + str(max(leaderboard_page - 1, 0)),
    }
    leaderboard_html = templates.inject('layout', {'page_content': templates.inject('leaderboard_layout', leaderboard_insert)})
    return leaderboard_html

def generate_leaderboard_entries(leaderboard_data, leaderboard_page):
    page_length = 25
    html = ''

    visible_scores = list(database.fetch_scores(leaderboard_data['score_ids']).sort('score', -1))[page_length * leaderboard_page : page_length * (leaderboard_page + 1)]
    user_ids = [score['user'] for score in visible_scores]
    score_users = database.get_users(user_ids)

    # use a hash map for quick assignment
    score_dict = {}
    for score in visible_scores:
        score_dict[score['user']] = score
    for user in score_users:
        score_dict[user.id]['user_obj'] = user

    # generate html
    for i, score in enumerate(visible_scores):
        entry_values = {
            'profile_picture': 'https://scoresaber.com/imports/images/usr-avatars/' + score['user_obj'].scoresaber_id + '.jpg',
            'score_rank': str(page_length * leaderboard_page + i + 1),
            'score_name': '<a href="/user/' + str(score['user']) + '">' + score['user_obj'].username + '</a>',
            'score_accuracy': str(round(score['score'] / max_score(leaderboard_data['notes']) * 100, 2)),
            'score_cr': str(0.0),
        }
        html += templates.inject('leaderboard_entry', entry_values)

    return html

def profile_page(user_id, profile_page):
    if profile_page == None:
        profile_page = 0
    else:
        profile_page = int(profile_page)

    profile_obj = Profile(user_id)
    profile_obj.load_scores()
    profile_insert = {}
    profile_insert.update(profile_obj.insert_info)
    profile_insert.update({
        'played_songs': generate_profile_entries(profile_obj, profile_page),
        'player_rank': str(1),
        'player_cr': str(0.00),
        'next_page': request.path.split('?')[0] + '?page=' + str(profile_page + 1),
        'last_page': request.path.split('?')[0] + '?page=' + str(max(profile_page - 1, 0)),
    })
    profile_html = templates.inject('layout', {'page_content': templates.inject('profile_layout', profile_insert)})
    return profile_html

def generate_profile_entries(profile_obj, profile_page):
    page_length = 10
    html = ''

    visible_scores = profile_obj.user.scores[profile_page * page_length : (profile_page + 1) * page_length]

    profile_obj.fetch_score_leaderboards(visible_scores)
    for score in visible_scores:
        inject_values = {
            'song_rank': str(score['rank']),
            'song_name': '<a href="/leaderboard/' + score['leaderboard']['key'] + '_' + shorten_settings(score['difficulty_settings']) + '">' + score['leaderboard']['name'] + '</a>',
            'cr_received': '0cr',
            'weighted_cr': '0cr',
            'accuracy': str(score['accuracy']),
            'song_pic': 'https://beatsaver.com' + score['leaderboard']['cover'],
        }
        html += templates.inject('profile_entry_layout', inject_values)
    return html

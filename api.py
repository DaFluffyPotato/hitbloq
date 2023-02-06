import json

from flask import jsonify

from db import database
from profile import Profile
from user import User
from general import mongo_clean, max_score, shorten_settings, lengthen_settings, epoch_ago
from cr_formulas import cr_accumulation_curve
import create_action
from templates import templates
from matchmaking import Matchmaking

mm = Matchmaking(database)

RANKED_LIST_DESCRIPTION = 'A collection of maps from the <map_pool_name> Hitbloq map pool used for the associated ranked ladder. Check out https://hitbloq.com for more info.'

def get_template(template_id):
    return jsonify({'id': template_id, 'template': templates.templates[template_id]})

def action_list():
    resp = list(database.get_actions(queue_id=-1))
    for action in resp:
        action['_id'] = str(action['_id'])
    return jsonify(resp)

def add_user(request_json, ip_address):
    ratelimits = database.get_rate_limits(ip_address)
    if ratelimits['user_additions'] < 2:
        database.ratelimit_add(ip_address, 'user_additions')
        create_action.create_user(request_json['url'])
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'ratelimit'})

def ranked_list(pool_id, offset=0, count=30):
    ranked_list_data = database.get_ranked_list(mongo_clean(pool_id))
    ranked_list_data['leaderboard_id_list'] = ranked_list_data['leaderboard_id_list'][offset:offset + count]
    return jsonify(ranked_list_data)

def ranked_list_detailed(pool_id, page=0, count=30):
    ranked_list_data = database.get_ranked_list(mongo_clean(pool_id))
    leaderboard_list = database.get_leaderboards(ranked_list_data['leaderboard_id_list'])

    leaderboard_list.sort(key=lambda x: x['star_rating'][pool_id] if pool_id in x['star_rating'] else 0, reverse=True)
    leaderboard_list = leaderboard_list[page * count : (page + 1) * count]

    output_data = []

    for leaderboard in leaderboard_list:
        star_rating = 0
        if pool_id in leaderboard['star_rating']:
            star_rating = leaderboard['star_rating'][pool_id]

        output_data.append({
            'song_cover': leaderboard['cover'],
            'song_name': leaderboard['name'],
            'song_id': leaderboard['hash'] + '_' + shorten_settings(leaderboard['difficulty_settings']),
            'song_plays': len(list(database.db['scores'].find({'song_id': leaderboard['_id']}))),
            'song_stars': star_rating,
            'song_difficulty': leaderboard['difficulty'][0].upper() + leaderboard['difficulty'][1:],
        })

    return jsonify(output_data)

def ranked_lists():
    return jsonify(database.get_pool_ids(False))

def get_announcement():
    return jsonify(database.db['config'].find_one({'_id': 'announcement'}))

def get_map_pools_detailed():
    map_pools = database.get_ranked_lists()

    response = []
    author_ids = []
    for pool in map_pools:
        for owner in pool['owners']:
            if owner not in author_ids:
                author_ids.append(owner)

    authors = list(database.db['discord_users'].find({'_id': {'$in': author_ids}}))
    authors_map = {}
    for author in authors:
        authors_map[str(author['_id'])] = author['tag'].split('#')[0]

    for pool in map_pools:
        authors_text = ''
        for i, author in enumerate(pool['owners']):
            if str(author) in authors_map:
                authors_text += authors_map[str(author)]
            else:
                authors_text += 'unknown'
            if i == len(pool['owners']) - 2:
                authors_text += ', and '
            elif i < len(pool['owners']) - 2:
                authors_text += ', '
        if authors_text == '':
            authors_text = 'unknown'

        response.append({
            'title': pool['shown_name'],
            'banner_title_hide': pool['banner_title_hide'],
            'author': authors_text,
            'banner_image': pool['cover'],
            'image': pool['playlist_cover'] if pool['playlist_cover'] else 'https://hitbloq.com/static/hitbloq.png',
            'id': pool['_id'],
            'description': pool['long_description'],
            'short_description': 'The ' + pool['shown_name'] + ' map pool.' if not pool['short_description'] else pool['short_description'],
            'player_count': pool['player_count'],
            'popularity': pool['priority'],
            'download_url': 'https://hitbloq.com/static/hashlists/' + pool['_id'] + '.bplist'
        })

    return jsonify(response)

def get_leaderboard_info(leaderboard_id):
    try:
        leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    except IndexError:
        return jsonify({'error': 'not found'})

    leaderboard_data['_id'] = str(leaderboard_data['_id'])
    return jsonify(leaderboard_data)

def get_leaderboard_scores(leaderboard_id, offset=0, count=30):
    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    score_data = list(database.db['scores'].find({'song_id': leaderboard_data['_id']}).sort('score', -1))[offset:offset + count]
    for score in score_data:
        del score['_id']
    return jsonify(score_data)

def extend_scores(leaderboard_data, score_data, base_rank, user_data=None):
    user_list = [score['user'] for score in score_data]
    if not user_data:
        user_data = {user.id : user for user in database.get_users(user_list)}

    for i, score in enumerate(score_data):
        if '_id' in score:
            del score['_id']
        score['username'] = user_data[score['user']].username
        score['accuracy'] = round(score['score'] / leaderboard_data['max_score'] * 100, 2)
        score['rank'] = base_rank + i + 1
        score['profile_pic'] = user_data[score['user']].profile_pic
        score['date_set'] = epoch_ago(score['time_set']) + ' ago'
        score['banner_image'] = user_data[score['user']].score_banner
        score['custom_color'] = user_data[score['user']].custom_color

    return score_data

def get_leaderboard_scores_extended(leaderboard_id, offset=0, count=10):
    # handle short settings format if necessary
    try:
        leaderboard_id = leaderboard_id.split('_')[0] + '|' + lengthen_settings('_'.join(leaderboard_id.split('_')[1:]))
    except KeyError:
        pass

    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    score_data = list(database.db['scores'].find({'song_id': leaderboard_data['_id']}).sort('score', -1))[offset:offset + count]
    score_data = extend_scores(leaderboard_data, score_data, offset)

    return jsonify(score_data)

def get_leaderboard_scores_nearby(leaderboard_id, user, extend=False):
    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    score_data = list(database.db['scores'].find({'song_id': leaderboard_data['_id']}).sort('score', -1))

    matched_index = -1
    for i, score in enumerate(score_data):
        if score['user'] == user:
            matched_index = i
    if matched_index == -1:
        return jsonify({})
    base_index = max(0, matched_index - 4)

    score_data = score_data[base_index : base_index + 10]

    user_list = [score['user'] for score in score_data]
    user_data = {user.id : user for user in database.get_users(user_list)}
    for i, score in enumerate(score_data):
        del score['_id']
        score['username'] = user_data[score['user']].username
        score['accuracy'] = round(score['score'] / leaderboard_data['max_score'] * 100, 2)
        score['rank'] = base_index + i + 1

    # TODO remove spaghetti with doubled up user requests
    if extend:
        score_data = extend_scores(leaderboard_data, score_data, base_index, user_data=user_data)

    return jsonify(score_data)

def leaderboard_scores_friends(leaderboard_id, friends_list, extend=False):
    # induce error if the request contents are invalid
    l = [int(v) for v in friends_list]

    leaderboard_data = list(database.get_leaderboards([leaderboard_id]))[0]
    score_data = list(database.db['scores'].find({'song_id': leaderboard_data['_id'], 'user': {'$in': friends_list}}).sort('score', -1))

    user_list = [score['user'] for score in score_data]
    user_data = {user.id : user for user in database.get_users(user_list)}
    for i, score in enumerate(score_data):
        del score['_id']
        score['username'] = user_data[score['user']].username
        score['accuracy'] = round(score['score'] / leaderboard_data['max_score'] * 100, 2)
        score['rank'] = i + 1

    # TODO remove spaghetti with doubled up user requests
    if extend:
        score_data = extend_scores(leaderboard_data, score_data, 0, user_data=user_data)

    return jsonify(score_data)

def ranked_ladder(pool_id, page, players_per_page=10, search=None):

    if search:
        aggregation_results = database.db['users'].aggregate([
            {'$match': {'username': {'$regex': search, '$options': 'i'}}},
            {'$lookup': {'from': 'za_pool_users_' + pool_id, 'localField': '_id', 'foreignField': '_id', 'as': 'pool_stats'}},
            {'$sort': {'pool_stats.0.cr_total': -1}},
            {'$limit': 50}
            ])

        users = [User().load(user, pool_id=pool_id) for user in list(aggregation_results)]

        output_data = {
            '_id': pool_id,
            'ladder': [],
        }

        for player in users:
            output_data['ladder'].append({
                'username': player.username,
                'rank': None,
                'profile_pic': player.profile_pic,
                'rank_change': None,
                'user': player.id,
                'banner_image': player.score_banner,
                'custom_color': player.custom_color,
                'cr': player.cr_totals[pool_id] if pool_id in player.cr_totals else 0,
            })

        return jsonify(output_data)

    else:
        ladder_data = database.get_ranking_slice(pool_id, page * players_per_page, (page + 1) * players_per_page)
        user_list = [user['user'] for user in ladder_data['ladder']]
        user_data = {user.id : user for user in database.get_users(user_list, pool_id=pool_id)}

        for i, player in enumerate(ladder_data['ladder']):
            player['username'] = user_data[player['user']].username
            player['rank'] = page * players_per_page + i + 1
            player['profile_pic'] = user_data[player['user']].profile_pic
            player['rank_change'] = user_data[player['user']].rank_change(pool_id, player['rank'])
            player['banner_image'] = user_data[player['user']].score_banner
            player['custom_color'] = user_data[player['user']].custom_color

        return jsonify(ladder_data)

def ranked_ladder_nearby(pool_id, user_id):
    players_per_page = 10

    users = database.get_users([user_id], pool_id=pool_id)
    base_index = 0
    if len(users):
        user = users[0]
        player_rank = database.get_user_ranking(user, pool_id)

        base_index = max(0, player_rank - 5)

    ladder_data = database.get_ranking_slice(pool_id, base_index, base_index + players_per_page)

    user_list = [user['user'] for user in ladder_data['ladder']]
    user_data = {user.id : user for user in database.get_users(user_list)}

    for i, player in enumerate(ladder_data['ladder']):
        player['username'] = user_data[player['user']].username
        player['rank'] = base_index + i + 1
        player['banner_image'] = user_data[player['user']].score_banner
        player['custom_color'] = user_data[player['user']].custom_color
        player['profile_pic'] = user_data[player['user']].profile_pic

    return jsonify(ladder_data)

def ranked_ladder_friends(pool_id, friends_list):
    ladder_data = {
        '_id': pool_id,
        'ladder': [],
    }

    friend_users = sorted(database.get_users(friends_list, pool_id=pool_id), key=lambda x: x.cr_totals[pool_id], reverse=True)

    for i, friend in enumerate(friend_users):
        ladder_data['ladder'].append({
            'rank': i + 1,
            'user': friend.id,
            'cr': friend.cr_totals[pool_id],
            'username': friend.username,
            'banner_image': friend.score_banner,
            'custom_color': friend.custom_color,
            'profile_pic': friend.profile_pic,
        })

    return jsonify(ladder_data)

def get_user_scores(user_id, pool_id, sort_mode='cr', page=0, count=10):
    page_length = count
    profile_obj = Profile(user_id)
    pool_data = profile_obj.user.load_pool_scores(database, pool_id)

    scores_by_cr = None
    if sort_mode == 'newest':
        profile_obj.user.scores.sort(key=lambda x : x['time_set'], reverse=True)
    elif sort_mode == 'oldest':
        profile_obj.user.scores.sort(key=lambda x : x['time_set'])
    else:
        profile_obj.user.scores.sort(key=lambda x : x['cr'][pool_id], reverse=True)
        scores_by_cr = profile_obj.user.scores

    # a copy of the scores ordered by CR is necessary to calculate the weighted cr for each score since it's based on index
    if not scores_by_cr:
        scores_by_cr = sorted(profile_obj.user.scores, key=lambda x : x['cr'][pool_id], reverse=True)

    visible_scores = profile_obj.user.scores[page * page_length : (page + 1) * page_length]

    score_data = []

    profile_obj.fetch_score_leaderboards(visible_scores)
    for i, score in enumerate(visible_scores):
        player_score_index = scores_by_cr.index(score)
        inject_values = {
            'song_rank': score['rank'],
            'song_name': score['leaderboard']['name'],
            'song_id': score['leaderboard']['hash'] + '_' + shorten_settings(score['song_id'].split('|')[1]),
            'cr_received': round(score['cr'][pool_id], 2),
            'weighted_cr': round(score['cr'][pool_id] * cr_accumulation_curve(player_score_index, pool_data['accumulation_constant']), 2),
            'accuracy': score['accuracy'],
            'song_cover': score['leaderboard']['cover'],
            'date_set': epoch_ago(score['time_set']) + ' ago',
            'time': score['time_set'],
            'difficulty': score['leaderboard']['difficulty'][0].upper() + score['leaderboard']['difficulty'][1:],
        }
        score_data.append(inject_values)

    return jsonify(score_data)

def ss_to_hitbloq_id(ss_id):
    matching_user = database.db['users'].find_one({'scoresaber_id': ss_id})
    if matching_user:
        return jsonify({'id': matching_user['_id']})
    else:
        return jsonify({'id': -1})

def mass_ss_to_hitbloq_id(id_list):
    # crash out if invalid IDs
    v = [int(ss_id) for ss_id in id_list]

    matching_users = database.db['users'].find({'scoresaber_id': {'$in': id_list}})

    result = [{'id': user['_id'], 'scoresaber_id': user['scoresaber_id']} for user in matching_users]

    return jsonify(result)

def player_rank_base(pool_id, users, short=False):
    pool_data = database.get_ranked_list(pool_id)

    player_rank = 0
    player_name = None
    player_cr = 0
    player_tier = 'none'
    player_scores = 0
    rank_history = []
    player_rank_ratio = 1
    if len(users):
        user = users[0]

        if not short:
            user.load_pool_scores(database, pool_id)

            rank_history = user.rank_history[pool_id] if pool_id in user.rank_history else [0, 0]

            player_scores = len(user.scores)

        player_name = user.username
        if pool_id in user.cr_totals:
            player_rank = database.get_user_ranking(user, pool_id)
            player_cr = round(user.cr_totals[pool_id], 2)

        if pool_data:
            player_rank_ratio = (player_rank - 1) / (pool_data['player_count'] if pool_data['player_count'] else player_rank)
            if player_cr == 0:
                player_tier = 'none'
            if player_rank_ratio < 0.001:
                player_tier = 'mystic'
            elif player_rank_ratio < 0.01:
                player_tier = 'myth'
            elif player_rank_ratio < 0.025:
                player_tier = 'master'
            elif player_rank_ratio < 0.07:
                player_tier = 'diamond'
            elif player_rank_ratio < 0.15:
                player_tier = 'platinum'
            elif player_rank_ratio < 0.25:
                player_tier = 'gold'
            elif player_rank_ratio < 0.5:
                player_tier = 'silver'
            else:
                player_tier = 'bronze'

    if short:
        response = {
            'rank': player_rank,
            'cr': player_cr,
            'tier': 'default/' + player_tier,
            'pool': pool_id,
            'pool_shown_name': pool_data['shown_name'],
            'ratio': player_rank_ratio,
        }
    else:
        response = {
            'username': player_name,
            'rank': player_rank,
            'cr': player_cr,
            'tier': 'default/' + player_tier,
            'ranked_score_count': player_scores,
            'history': rank_history,
            'pool': pool_id,
            'pool_shown_name': pool_data['shown_name'],
            'ratio': player_rank_ratio,
        }

    return response


def player_rank_api(pool_id, user):
    users = database.get_users([user], pool_id=pool_id)
    return jsonify(player_rank_base(pool_id, users))

def player_ranks_api(pool_ids, user):
    users = database.get_users([user])

    for pool_id in pool_ids:
        users[0].load_pool_stats(database, pool_id)

    # don't do more than 20 pools
    pool_ids = pool_ids[:20]

    ranks_data = sorted([player_rank_base(pool_id, users, short=True) for pool_id in pool_ids], key=lambda x : x['rank'])
    return jsonify(ranks_data)

def user_basic_api(user_id):
    try:
        user = database.get_users([user_id])[0]
        user_data = user.jsonify()
        return jsonify(user_data)
    except IndexError:
        return jsonify({})

def action_id_status(action_id):
    exists = database.action_exists(action_id)
    return jsonify({'exists': exists})

def ss_registered(ss_id):
    matching_user = database.db['users'].find_one({'scoresaber_id': ss_id})
    if matching_user:
        if matching_user['last_update'] != 0:
            return jsonify({'registered': True, 'user': matching_user['_id']})
        else:
            return jsonify({'registered': False, 'user': matching_user['_id']})
    return jsonify({'registered': False, 'user': None})

def get_current_event():
    current_event_id = database.db['events'].find_one({'_id': 'current_event'})['event_id']
    current_event = database.db['events'].find_one({'_id': current_event_id})

    if current_event == None:
        current_event = {'id': -1}
    else:
        current_event['id'] = current_event['_id']
        del current_event['_id']

    return jsonify(current_event)

def get_popular_pools(threshold):
    popular_pools = [pool['_id'] for pool in database.db['ranked_lists'].find({}, {'_id': 1, 'priority': 1}).sort('priority', -1).limit(threshold)]

    return jsonify(popular_pools)

def get_player_badges(user_id):
    user = database.db['users'].find_one({'_id': user_id})
    response = []
    if user:
        user_badges = user['badges']
        badge_data = {badge['_id'] : badge for badge in database.db['badges'].find({'_id': {'$in': user_badges}})}
        for badge in user_badges:
            if badge in badge_data:
                response.append(badge_data[badge])
    return jsonify(response)

def action_queue_statuses():
    return jsonify(database.action_queue_status())

def pool_feed(pool_id):
    recent_updates = list(database.db['pool_feeds'].aggregate([{'$match': {'pool': pool_id}}, {'$lookup': {'from': 'leaderboards', 'localField': 'leaderboard_id', 'foreignField': '_id', 'as': 'leaderboard_data'}}, {'$sort': {'time': -1}}, {'$limit': 16}]))
    for update in recent_updates:
        del update['_id']
        update['date'] = epoch_ago(update['time'])
        update['short_leaderboard_id'] = update['leaderboard_data'][0]['hash'] + '_' + shorten_settings(update['leaderboard_data'][0]['difficulty_settings'])
    return jsonify(recent_updates)

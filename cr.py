from db import database
from general import max_score
from config import LEADERBOARD_VOTE_RANKING_CURVE_CONSTANT
from cr_formulas import *

def update_leaderboard_cr(leaderboard_id):
    leaderboard = database.get_leaderboards([leaderboard_id])[0]
    scores = list(database.fetch_scores(leaderboard['score_ids']))
    if len(scores) != 0:
        for score in scores:
            score['cr'] = calculate_cr(score['score'] / max_score(leaderboard['notes']) * 100, leaderboard['star_rating'])
        database.replace_scores(scores)

def update_leaderboards_cr(leaderboard_ids):
    for leaderboard_id in leaderboard_ids:
        update_leaderboard_cr(leaderboard_id)

def calculate_song_rankings(user, leaderboards):
    user.load_scores(database)

    pool_leaderboard_list = list(leaderboards)

    scores_for_sort = []
    for score in user.scores:
        leaderboard_id = score['song_id']
        if leaderboard_id in pool_leaderboard_list:
                scores_for_sort.append([score['score'] / max_score(leaderboards[leaderboard_id]), leaderboard_id, score['_id']])
    scores_for_sort.sort(reverse=True)
    return scores_for_sort

def load_map_pools(map_pools):
    pool_leaderboard_list = []
    for pool in map_pools:
        pool_data = database.get_ranked_list(pool)
        pool_leaderboard_list += pool_data['leaderboard_id_list']

    pool_leaderboard_list = list(set(pool_leaderboard_list))

    leaderboards = {leaderboard['_id'] : leaderboard for leaderboard in database.get_leaderboards(pool_leaderboard_list)}
    return leaderboards


def full_cr_update(map_pools):
    rankings = []
    user_list = database.search_users({})
    leaderboards = load_map_pools(map_pools)
    leaderboard_notes = {k : v['notes'] for (k, v) in leaderboards.items()}

    for leaderboard in leaderboards:
        leaderboards[leaderboard]['votes'] = {}
    for user in user_list:
        votes = calculate_song_rankings(user, leaderboard_notes)
        for i, vote in enumerate(votes):
            leaderboards[vote[1]]['votes'][vote[2]] = i / (len(votes) - 1)

    for leaderboard in leaderboards:
        leaderboard = leaderboards[leaderboard]

        difficulty_vote_weight_total = 0
        difficulty_vote_total = 0

        i = 0
        for score_id in leaderboard['score_ids']:
            if score_id in leaderboard['votes']:
                vote_weight = calculate_weight(LEADERBOARD_VOTE_RANKING_CURVE_CONSTANT, i)
                difficulty_vote_weight_total += vote_weight
                difficulty_vote_total += leaderboard['votes'][score_id] * vote_weight
                i += 1

        if difficulty_vote_weight_total == 0:
            continue

        difficulty_rating = round(difficulty_vote_total / difficulty_vote_weight_total * 19 + 1, 2)

        database.update_leaderboard_data(leaderboard['_id'], {'$set': {'star_rating': difficulty_rating}})

        rankings.append([difficulty_rating, leaderboard['name']])

    rankings.sort(reverse=True)

    update_leaderboards_cr(leaderboards.keys())

    for user in user_list:
        database.update_user_cr_total(user)
        # TODO: redo this code to update all the leaderboards in one shot since all the scores must be updated
        for map_pool_id in map_pools:
            database.update_user_ranking(user, map_pool_id)

    return rankings

if __name__ == "__main__":
    rankings = full_cr_update(['global_main', 'blank_dummy'])
    for song in rankings:
        print(song[1] + ':', song[0])

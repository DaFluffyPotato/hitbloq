from db import database
from general import max_score
from config import LEADERBOARD_VOTE_RANKING_CURVE_CONSTANT
from cr_formulas import *

SCORE_CONSIDERATION_RANGE = 100

class CRRecalc:
    def __init__(self, pool_id, debug=False, action_id=None):
        self.db = database.db
        self.pool_id = pool_id
        self.pool_data = None

        self.action_id = action_id

        self.user_scores = {}
        self.user_rank_ratios = {}
        self.leaderboard_scores = {}
        self.old_ratings = {}
        self.max_scores = {}
        self.updated_map_difficulties = {}

        self.skip_list = {}

        self.vote_curve_constant = LEADERBOARD_VOTE_RANKING_CURVE_CONSTANT

        self.debug = debug

    def get_pool_data(self):
        self.pool_data = self.db['ranked_lists'].find_one({'_id': self.pool_id})
        if self.debug:
            print('got leaderboard list')

    def create_score_mappings(self):
        for i, leaderboard_id in enumerate(self.pool_data['leaderboard_id_list']):
            if self.debug:
                print('getting scores for leaderboard', i + 1, '/', len(self.pool_data['leaderboard_id_list']))

            # get leaderboard info
            leaderboard_data = self.db['leaderboards'].find_one({'_id': leaderboard_id})
            leaderboard_max_score = max_score(leaderboard_data['notes'])
            self.max_scores[leaderboard_id] = leaderboard_max_score

            # add to skip list if necessary
            if self.pool_id in leaderboard_data['forced_star_rating']:
                self.skip_list[leaderboard_id] = leaderboard_data['forced_star_rating'][self.pool_id]

            # log original rating
            if self.pool_id in leaderboard_data['star_rating']:
                self.old_ratings[leaderboard_id] = leaderboard_data['star_rating'][self.pool_id]
            else:
                self.old_ratings[leaderboard_id] -1

            # get applicable scores
            leaderboard_scores = self.db['scores'].find({'song_id': leaderboard_id}).sort('score', -1).limit(SCORE_CONSIDERATION_RANGE)

            # iterate through sorted scores and assign to players/leaderboards
            self.leaderboard_scores[leaderboard_id] = []

            for score in leaderboard_scores:
                self.leaderboard_scores[leaderboard_id].append(score['user'])
                if score['user'] not in self.user_scores:
                    self.user_scores[score['user']] = []
                # assign score to player with the proper accuracy for the score
                self.user_scores[score['user']].append((score['score'] / leaderboard_max_score, leaderboard_id))


        if self.debug:
            print('mapping player difficulty ratings...')

        # map player's difficulty rating for each leaderboard in a leaderboard:difficulty pair
        for user in list(self.user_scores):
            self.user_scores[user].sort()
            self.user_rank_ratios[user] = {}

            user_score_count = len(self.user_scores[user])
            ratio_increment = 1 / user_score_count
            for i, score in enumerate(self.user_scores[user]):
                self.user_rank_ratios[user][score[1]] = 1 - i * ratio_increment

            # clear out unnecessary data to save RAM
            del self.user_scores[user]

    def generate_leaderboard_difficulties(self):
        for leaderboard_id in self.pool_data['leaderboard_id_list']:
            map_difficulty = 0

            # add exception case for when a leaderboard has no scores
            if not len(self.leaderboard_scores[leaderboard_id]):
                map_difficulty = 0

            # main case
            else:
                if leaderboard_id in self.skip_list:
                    map_difficulty = self.skip_list[leaderboard_id]
                else:
                    total_weight = 0
                    total_difficulty = 0
                    for i, user in enumerate(self.leaderboard_scores[leaderboard_id]):
                        weight = calculate_weight(self.vote_curve_constant, i)
                        total_weight += weight
                        total_difficulty += self.user_rank_ratios[user][leaderboard_id] * weight

                    map_difficulty = total_difficulty / total_weight

            self.updated_map_difficulties[leaderboard_id] = (map_difficulty, (leaderboard_id in self.skip_list))

    def adjust_difficulty_results(self):
        new_ratings = {}
        for leaderboard in self.updated_map_difficulties:
            if not self.updated_map_difficulties[leaderboard][1]:
                new_ratings[leaderboard] = round(self.updated_map_difficulties[leaderboard][0] * 20, 2)
            else:
                new_ratings[leaderboard] = round(self.updated_map_difficulties[leaderboard][0], 2)
        return new_ratings

    def update_leaderboard_cr_rewards(self, new_ratings):
        for leaderboard_id in self.pool_data['leaderboard_id_list']:
            if (self.old_ratings[leaderboard_id] != new_ratings[leaderboard_id]) or (self.pool_data['force_recalc']):
                leaderboard_scores = list(self.db['scores'].find({'song_id': leaderboard_id}))

                # update star rating
                self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$set': {'star_rating.' + self.pool_id: new_ratings[leaderboard_id]}})

                # update score CR rewards
                for score in leaderboard_scores:
                    score['cr'][self.pool_id] = calculate_cr(score['score'] / self.max_scores[leaderboard_id] * 100, new_ratings[leaderboard_id], self.pool_data['cr_curve'])

                # apply changes
                if len(leaderboard_scores):
                    database.replace_scores(leaderboard_scores)

    def run(self):
        if self.debug:
            print('starting')

        self.get_pool_data()
        if self.action_id:
            database.set_action_progress(self.action_id, 0.1)

        self.create_score_mappings()
        if self.action_id:
            database.set_action_progress(self.action_id, 0.2)

        self.generate_leaderboard_difficulties()
        if self.action_id:
            database.set_action_progress(self.action_id, 0.5)

        new_ratings = self.adjust_difficulty_results()
        if self.action_id:
            database.set_action_progress(self.action_id, 0.6)

        self.update_leaderboard_cr_rewards(new_ratings)

        database.set_action_progress(self.action_id, 0.9)
        self.db['ranked_lists'].update_one({'_id': self.pool_id}, {'$set': {'needs_cr_total_recalc': True, 'force_recalc': False}})

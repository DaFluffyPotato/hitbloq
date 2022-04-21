import time

import scoresaber

class User():
    def __init__(self):
        # direct db values
        self.username = 'null'
        self.id = -1
        self.scoresaber_id = 'null'
        self.score_banner = None
        self.profile_banner = None
        self.profile_background = None
        self.last_update = 0
        self.cr_totals = {}
        self.date_created = 0
        self.max_rank = {}
        self.rank_history = {}
        self.last_manual_refresh = 0
        self.badges = []
        self.custom_color = None

        # temp values
        self.scores = []

    def generate_rank_info(self, database, map_pool):
        pool_data = self.load_pool_scores(database, map_pool)

        if map_pool not in self.cr_totals:
            self.load_pool_stats(database, map_pool)

        player_cr_total = 0
        if map_pool in self.cr_totals:
            player_cr_total = self.cr_totals[map_pool]

        player_max_rank = 0
        if map_pool in self.max_rank:
            player_max_rank = self.max_rank[map_pool]

        player_rank = database.get_user_ranking(self, map_pool)

        player_rank_ratio = (player_rank - 1) / (pool_data['player_count'] if pool_data['player_count'] else player_rank - 1)

        if self.scores == []:
            player_tier = 'none'
        elif player_rank_ratio < 0.001:
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

        self.pool_tier = player_tier
        self.pool_rank = player_rank
        self.pool_max_rank = player_max_rank
        self.pool_cr_total = player_cr_total

        return pool_data

    def rank_change(self, pool_id, current_rank):
        if not len(self.rank_history[pool_id]):
            self.rank_history[pool_id].append(current_rank)
        self.rank_history[pool_id].append(current_rank)
        user_change = self.rank_history[pool_id][max(-7, -len(self.rank_history[pool_id]))] - self.rank_history[pool_id][-1]
        return user_change

    def refresh_scores(self, database, action_id=None, queue_id=0):
        database.update_user_scores(self, action_id, queue_id)

    def refresh(self, database):
        ss_profile = scoresaber.ScoresaberInterface(database).ss_req('player/' + self.scoresaber_id + '/basic')
        self.username = ss_profile['name'].replace('<', '&lt;').replace('>', '&gt;')
        self.profile_pic = ss_profile['profilePicture']
        database.db['users'].update_one({'_id': self.id}, {'$set': {'profile_pic': self.profile_pic, 'username': self.username}})

    def create(self, database, scoresaber_id):
        scoresaber_id = scoresaber_id.split('/')[-1]
        try:
            a = int(scoresaber_id)
        except:
            print('scoresaber_id invalid')
            return None

        if len(list(database.db['users'].find({'scoresaber_id': scoresaber_id}))):
            print('user', scoresaber_id, 'is a duplicate!')
            return None

        ss_profile = scoresaber.ScoresaberInterface(database).ss_req('player/' + scoresaber_id + '/basic')
        try:
            self.username = ss_profile['name']
        except KeyError:
            print('attempted to create invalid user', scoresaber_id)
            return None

        pool_ids = database.get_pool_ids(False)

        self.profile_pic = ss_profile['profilePicture']
        self.id = database.gen_new_user_id()
        self.scoresaber_id = scoresaber_id
        self.last_update = 0
        self.date_created = time.time()
        self.score_banner = None
        self.profile_banner = None
        self.profile_background = None
        self.last_manual_refresh = 0
        self.custom_color = '#ffffff'

        self.cr_totals = {}

        for pool_id in pool_ids:
            pool_stats = {'_id': self.id, 'rank_history': [], 'cr_total': 0, 'max_rank': 999999999}
            database.db['za_pool_users_' + pool_id].insert_one(pool_stats)

        database.add_user(self)
        return self

    def load_pool_stats(self, database, pool_id):
        pool_stats = database.db['za_pool_users_' + pool_id].find_one({'_id': self.id})
        self.cr_totals[pool_id] = pool_stats['cr_total']
        self.rank_history[pool_id] = pool_stats['rank_history']
        self.max_rank[pool_id] = pool_stats['max_rank']

    def load(self, json_data, pool_id=None):
        self.username = json_data['username']
        self.id = json_data['_id']
        self.scoresaber_id = json_data['scoresaber_id']
        self.last_update = json_data['last_update']

        if pool_id:
            if 'pool_stats' in json_data:
                self.cr_totals = {pool_id: json_data['pool_stats'][0]['cr_total']}
                self.rank_history = {pool_id: json_data['pool_stats'][0]['rank_history']}
                self.max_rank = {pool_id: json_data['pool_stats'][0]['max_rank']}

        self.profile_pic = json_data['profile_pic']
        self.date_created = json_data['date_created']
        self.score_banner = json_data['score_banner']
        self.profile_banner = json_data['profile_banner']
        self.profile_background = json_data['profile_background']
        self.last_manual_refresh = json_data['last_manual_refresh']
        self.badges = json_data['badges']
        self.custom_color = json_data['custom_color']
        return self

    def jsonify(self):
        json_data = {
            '_id': self.id,
            'username': self.username,
            'scoresaber_id': self.scoresaber_id,
            'last_update': self.last_update,
            'profile_pic': self.profile_pic,
            'date_created': self.date_created,
            'score_banner': self.score_banner,
            'profile_banner': self.profile_banner,
            'profile_background': self.profile_background,
            'last_manual_refresh': self.last_manual_refresh,
            'badges': self.badges,
            'custom_color': self.custom_color,
        }
        return json_data

    def load_scores(self, database):
        self.scores = list(database.db['scores'].find({'user': self.id, 'cr': {'$ne': {}}}))

    def unload_scores(self):
        self.scores = []

    def load_pool_scores(self, database, map_pool_id):
        self.load_scores(database)
        map_pool = database.get_ranked_list(map_pool_id)
        new_scores = []
        self.scores_total = len(self.scores)
        for score in self.scores:
            if score['song_id'] in map_pool['leaderboard_id_list']:
                if map_pool_id not in score['cr']:
                    score['cr'][map_pool_id] = 0
                new_scores.append(score)
        self.scores = new_scores
        return map_pool

import time

import scoresaber

class User():
    def __init__(self):
        # direct db values
        self.username = 'null'
        self.id = -1
        self.scoresaber_id = 'null'
        self.score_banner = None
        self.score_ids = []
        self.last_update = 0
        self.cr_totals = {}
        self.date_created = 0
        self.max_rank = {}
        self.rank_history = {}

        # temp values
        self.scores = []

    def refresh_scores(self, database, action_id=None):
        database.update_user_scores(self, action_id)

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
            self.username = ss_profile['playerInfo']['playerName']
        except KeyError:
            print('attempted to create invalid user', scoresaber_id)
            return None

        self.profile_pic = 'https://new.scoresaber.com' + ss_profile['playerInfo']['avatar']
        self.id = database.gen_new_user_id()
        self.scoresaber_id = scoresaber_id
        self.score_ids = []
        self.last_update = 0
        self.date_created = time.time()
        self.max_rank = {}
        self.rank_history = {}
        self.score_banner = None

        self.cr_totals = {pool_id : 0 for pool_id in database.get_pool_ids(False)}

        database.add_user(self)
        return self

    def load(self, json_data):
        self.username = json_data['username']
        self.id = json_data['_id']
        self.scoresaber_id = json_data['scoresaber_id']
        self.score_ids = json_data['score_ids']
        self.last_update = json_data['last_update']
        self.cr_totals = json_data['total_cr']
        self.profile_pic = json_data['profile_pic']
        self.date_created = json_data['date_created']
        self.max_rank = json_data['max_rank']
        self.rank_history = json_data['rank_history']
        self.score_banner = json_data['score_banner']
        return self

    def jsonify(self):
        json_data = {
            '_id': self.id,
            'username': self.username,
            'scoresaber_id': self.scoresaber_id,
            'score_ids': self.score_ids,
            'last_update': self.last_update,
            'total_cr': self.cr_totals,
            'profile_pic': self.profile_pic,
            'date_created': self.date_created,
            'max_rank': self.max_rank,
            'rank_history': self.rank_history,
            'score_banner': self.score_banner,
        }
        return json_data

    def load_scores(self, database):
        self.scores = list(database.fetch_scores(self.score_ids))

    def load_pool_scores(self, database, map_pool_id):
        self.load_scores(database)
        map_pool = database.get_ranked_list(map_pool_id)
        new_scores = []
        self.scores_total = len(self.scores)
        for score in self.scores:
            if score['song_id'] in map_pool['leaderboard_id_list']:
                new_scores.append(score)
        self.scores = new_scores

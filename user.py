import scoresaber

class User():
    def __init__(self):
        # direct db values
        self.username = 'null'
        self.id = -1
        self.scoresaber_id = 'null'
        self.score_ids = []
        self.last_update = 0
        self.cr_totals = {}

        # temp values
        self.scores = []

    def refresh_scores(self, database):
        database.update_user_scores(self)

    def create(self, database, scoresaber_id):
        ss_profile = scoresaber.ScoresaberInterface(database).ss_req('player/' + scoresaber_id + '/basic')
        self.username = ss_profile['playerInfo']['playerName']
        self.profile_pic = 'https://new.scoresaber.com' + ss_profile['playerInfo']['avatar']
        self.id = database.gen_new_user_id()
        self.scoresaber_id = scoresaber_id
        self.score_ids = []
        self.last_update = 0

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
        }
        return json_data

    def load_scores(self, database):
        self.scores = list(database.fetch_scores(self.score_ids))

    def load_pool_scores(self, database, map_pool_id):
        self.load_scores(database)
        map_pool = database.get_ranked_list(map_pool_id)
        new_scores = []
        for score in self.scores:
            if score['song_id'] in map_pool['leaderboard_id_list']:
                new_scores.append(score)
        self.scores = new_scores

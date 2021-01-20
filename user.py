import scoresaber

class User():
    def __init__(self):
        # direct db values
        self.username = 'null'
        self.id = -1
        self.scoresaber_id = 'null'
        self.score_ids = []
        self.last_update = 0

        # temp values
        self.scores = []

    def create(self, database, username, scoresaber_id):
        self.username = username
        self.id = database.gen_new_user_id()
        self.scoresaber_id = scoresaber_id
        self.score_ids = []
        self.last_update = 0
        database.add_user(self)
        return self

    def load(self, json_data):
        self.username = json_data['username']
        self.id = json_data['_id']
        self.scoresaber_id = json_data['scoresaber_id']
        self.score_ids = json_data['score_ids']
        self.last_update = json_data['last_update']
        return self

    def jsonify(self):
        json_data = {
            '_id': self.id,
            'username': self.username,
            'scoresaber_id': self.scoresaber_id,
            'score_ids': self.score_ids,
            'last_update': self.last_update,
        }
        return json_data

    def load_scores(self, database):
        self.scores = list(database.fetch_scores(self.score_ids))

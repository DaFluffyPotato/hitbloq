import pymongo

from general import max_score
from db import database

class Profile:
    def __init__(self, user_id):
        self.user = database.get_users([user_id])[0]
        self.insert_info = {
            'player_name': self.user.username,
            'player_pic': self.user.profile_pic,
        }

    def load_scores(self):
        self.user.load_scores(database)

    def fetch_score_leaderboards(self, score_set):
        leaderboard_ids = [score['song_id'] for score in score_set]
        leaderboard_data = database.get_leaderboards(leaderboard_ids)

        # match leaderboard data from mongo to the dataset given
        for score in score_set:
            for leaderboard in leaderboard_data:
                if score['song_id'] == leaderboard['_id']:
                    score['leaderboard'] = leaderboard
                    score['rank'] = [leaderboard_score['_id'] for leaderboard_score in database.db['scores'].find({'song_id': score['song_id']}).sort('score', pymongo.DESCENDING)].index(score['_id']) + 1
                    score['accuracy'] = round(score['score'] / max(1, score['leaderboard']['max_score']) * 100, 2)

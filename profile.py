from general import max_score
from db import database

class Profile:
    def __init__(self, user_id):
        self.user = database.get_users([user_id])[0]
        self.insert_info = {
            'player_name': self.user.username,
            'player_pic': 'https://scoresaber.com/imports/images/usr-avatars/' + self.user.scoresaber_id + '.jpg',
        }

    def load_scores(self):
        self.user.load_scores(database)

    def fetch_score_leaderboards(self, score_set):
        leaderboard_ids = [score['song_hash'] + '|' + score['difficulty_settings'] for score in score_set]
        leaderboard_data = database.get_leaderboards(leaderboard_ids)

        # match leaderboard data from mongo to the dataset given
        for score in score_set:
            for leaderboard in leaderboard_data:
                if (score['song_hash'] == leaderboard['_id'].split('|')[0]) and (score['difficulty_settings'] == leaderboard['_id'].split('|')[1]):
                    score['leaderboard'] = leaderboard
                    score['rank'] = score['leaderboard']['score_ids'].index(score['_id']) + 1
                    score['accuracy'] = round(score['score'] / max_score(score['leaderboard']['notes']) * 100, 2)

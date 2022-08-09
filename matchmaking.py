import time
from config_loader import config

DEFAULT_RATING = 1000

class Matchmaking:
    def __init__(self, db):
        self.db = db

    def profile(self, user_id):
        user = self.db.db['users'].find_one({'_id': user_id})
        if not user:
            user = self.db.db['users'].find_one({'scoresaber_id': user_id})
        if not user:
            return {}

        mm_user = self.db.db['mm_users'].find_one({'_id': user['_id']})

        # generate user data if not found
        if user and not mm_user:
            mm_user = {
                '_id': user['_id'],
                'scoresaber_id': user['scoresaber_id'],
                'rating': DEFAULT_RATING,
                'username': user['username'],
            }

            self.db.db['mm_users'].insert_one(mm_user)

        return mm_user

    def pools(self):
        return {'pools': self.db.db['config'].find_one({'_id': 'mm_pools'})['pools']}

    def submit_match(self, match_data):
        print(match_data)

        required_fields = ('key', 'players', 'pool', 'left', 'maps')
        for field in required_fields:
            if field not in match_data:
                return {'error': 'invalid fields'}

        match_key = match_data['key']
        match_host = None
        for known_host in config['mm_keys']:
            if config['mm_keys'][known_host] == match_key:
                match_host = known_host
        if not known_host:
            return {'error': 'invalid key'}

        match_data['host'] = match_host

        player_wins = {player: 0 for player in match_data['players']}
        for map in match_data['maps']:
            max_score = [-1, []]
            for i, score in enumerate(map['scores']):
                if score >= max_score[0]:
                    if score > max_score[0]:
                        max_score = [score, []]
                    max_score[1].append(i)
            for winner in max_score[1]:
                player_wins[match_data['players'][i]] += 1

        related_players = self.db.db['mm_users'].find({'scoresaber_id': {'$in': [match_data['players']]}})
        player_info = {player['scoresaber_id']: {'rating': player['rating'], 'id': player['_id']} for player in related_players}
        match_data['player_info'] = player_info
        match_data['wins'] = player_wins
        match_data['timestamp'] = time.time()
        del match_data['key']

        self.db.db['mm_matches'].insert_one(match_data)

        if '_id' in match_data:
            del match_data['_id']

        return match_data

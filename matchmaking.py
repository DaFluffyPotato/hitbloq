import time
from config_loader import config

DEFAULT_RATING = 1000
EXPECTED_SCORE_CONSTANT = 400
ELO_K = 16 # done per map

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
                'rating': {pool: DEFAULT_RATING for pool in self.pools()['pools']},
                'username': user['username'],
            }

            self.db.db['mm_users'].insert_one(mm_user)

        return mm_user

    def pools(self):
        return {'pools': self.db.db['config'].find_one({'_id': 'mm_pools'})['pools']}

    def elo_calc(self, wins, ratings):
        total_score = sum(wins.values())
        p1, p2 = list(ratings)[:2]
        p1_score = wins[p1]
        p2_score = wins[p2]
        p1_expected_score = total_score / (1 + 10 ** ((ratings[p2] - ratings[p1]) / EXPECTED_SCORE_CONSTANT))
        p2_expected_score = total_score / (1 + 10 ** ((ratings[p1] - ratings[p2]) / EXPECTED_SCORE_CONSTANT))
        p1_rating_change = ELO_K * total_score * (p1_score - p1_expected_score)
        p2_rating_change = ELO_K * total_score * (p2_score - p2_expected_score)
        return {p1: p1_rating_change, p2: p2_rating_change}

    def submit_match(self, match_data):
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

        if match_data['pool'] not in self.pools()['pools']:
            return {'error': 'invalid pool'}

        if len(match_data['players']) != 2:
            return {'error': 'only 2 player matches are supported for now'}

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

        related_players = self.db.db['mm_users'].find({'scoresaber_id': {'$in': match_data['players']}})
        player_info = {player['scoresaber_id']: {'rating': player['rating'][match_data['pool']], 'id': player['_id']} for player in related_players}
        match_data['player_info'] = player_info
        match_data['wins'] = player_wins
        match_data['timestamp'] = time.time()
        del match_data['key']

        rating_changes = self.elo_calc(match_data['wins'], {p: player_info[p]['rating'] for p in player_info})
        match_data['rating_changes'] = rating_changes

        self.db.db['mm_matches'].insert_one(match_data)

        if '_id' in match_data:
            del match_data['_id']

        return match_data

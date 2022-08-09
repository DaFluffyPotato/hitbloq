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

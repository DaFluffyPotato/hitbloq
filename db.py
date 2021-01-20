import time
from getpass import getpass

import pymongo

import scoresaber, beatsaver
import user
import config

class HitbloqMongo():
    def __init__(self, password):
        self.client = pymongo.MongoClient('mongodb://dafluffypotato:' + password + '@dafluffypotato-db-shard-00-00-b1wgg.mongodb.net:27017,dafluffypotato-db-shard-00-01-b1wgg.mongodb.net:27017,dafluffypotato-db-shard-00-02-b1wgg.mongodb.net:27017/test?ssl=true&replicaSet=DaFluffyPotato-DB-shard-0&authSource=admin&retryWrites=true&w=majority', connectTimeoutMS=30000, socketTimeoutMS=None, connect=False, maxPoolsize=1)
        self.db = self.client['hitbloq_com']

    def gen_new_user_id(self):
        return self.db['counters'].find_and_modify(query={'type': 'user_id'}, update={'$inc': {'count': 1}})['count']

    def add_user(self, user):
        self.db['users'].insert_one(user.jsonify())

    def get_users(self, users):
        return [user.User().load(user_found) for user_found in self.db['users'].find({'_id': {'$in': users}})]

    def update_user(self, user, update=None):
        if update:
            self.db['users'].update_one({'_id': user.id}, update)
        else:
            self.db['users'].replace_one({'_id': user.id}, user.jsonify())

    def update_user_scores(self, user):
        scoresaber_api = scoresaber.ScoresaberInterface(self.db)
        new_scores = scoresaber_api.fetch_until(user.scoresaber_id, user.last_update)
        for score in new_scores:
            self.add_score(user, score)
        self.update_user(user, {'$set': {'last_update': time.time()}})

    def format_score(self, user, scoresaber_json):
        score_data = {
            # typo in scoresaber api. lul
            'score': scoresaber_json['unmodififiedScore'],
            'time_set': scoresaber_json['epochTime'],
            'song_hash': scoresaber_json['songHash'],
            'difficulty_settings': scoresaber_json['difficultyRaw'],
            'cr': 0,
            'user': user.id,
        }
        return score_data

    def delete_scores(self, leaderboard_id, score_id_list):
        self.db['scores'].delete_many({'_id': {'$in': score_id_list}})
        self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$pull': {'score_ids': {'$in': score_id_list}}})

    def fetch_scores(self, score_id_list):
        return self.db['scores'].find({'_id': {'$in': score_id_list}}).sort('time_set', -1)

    def add_score(self, user, scoresaber_json):
        leaderboard_id = scoresaber_json['songHash'] + '|' + scoresaber_json['difficultyRaw']
        valid_leaderboard = True
        if len(list(self.db['leaderboards'].find({'_id': leaderboard_id}))) == 0:
            valid_leaderboard = self.create_leaderboard(leaderboard_id, scoresaber_json['songHash'])

        if valid_leaderboard:
            # delete old score data
            matching_scores = self.db['scores'].find({'user': user.id, 'song_hash': scoresaber_json['songHash'], 'difficulty_settings': scoresaber_json['difficultyRaw']})
            matching_scores = [score['_id'] for score in matching_scores]
            self.delete_scores(leaderboard_id, matching_scores)

            # add new score
            mongo_response = self.db['scores'].insert_one(self.format_score(user, scoresaber_json))
            inserted_id = mongo_response.inserted_id
            self.update_user(user, {'$push': {'score_ids': inserted_id}})
            self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$push': {'score_ids': inserted_id}})
            self.refresh_score_order(leaderboard_id)

    def refresh_score_order(self, leaderboard_id):
        leaderboard_data = self.db['leaderboards'].find_one({'_id': leaderboard_id})
        new_score_order = [score['_id'] for score in self.fetch_scores(leaderboard_data['score_ids']).sort('score', -1)]
        self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$set': {'score_ids': new_score_order}})

    def create_leaderboard(self, leaderboard_id, leaderboard_hash):
        print('Creating leaderboard:', leaderboard_id)

        # remove old instances
        self.db['leaderboards'].delete_many({'_id': leaderboard_id})

        leaderboard_difficulty = leaderboard_id.split('|')[-1]

        beatsaver_api = beatsaver.BeatSaverInterface()
        beatsaver_data = beatsaver_api.lookup_song_hash(leaderboard_hash)

        if beatsaver_data:
            characteristic = leaderboard_difficulty.split('_')[-1]
            characteristic = config.CHARACTERISTIC_CONVERSION[characteristic]

            difficulty = leaderboard_difficulty.split('_')[1]
            difficulty = config.DIFFICULTY_CONVERSION[difficulty]

            # get the correct difficulty data based on characteristic and difficulty
            difficulty_data = [c['difficulties'] for c in beatsaver_data['metadata']['characteristics'] if c['name'] == characteristic][0][difficulty]

            leaderboard_data = {
                '_id': leaderboard_id,
                'key': beatsaver_data['key'],
                'cover': beatsaver_data['coverURL'],
                'name': beatsaver_data['metadata']['songName'],
                'sub_name': beatsaver_data['metadata']['songSubName'],
                'artist': beatsaver_data['metadata']['songAuthorName'],
                'mapper': beatsaver_data['metadata']['levelAuthorName'],
                'bpm': beatsaver_data['metadata']['bpm'],
                'difficulty_settings': leaderboard_id.split('|')[-1],
                'difficulty': difficulty,
                'characteristic': characteristic,
                'duration': beatsaver_data['metadata']['duration'],
                'difficulty_duration': difficulty_data['duration'],
                'length': difficulty_data['length'],
                'njs': difficulty_data['njs'],
                'bombs': difficulty_data['bombs'],
                'notes': difficulty_data['notes'],
                'obstacles': difficulty_data['obstacles'],
                'hash': leaderboard_hash,
                'score_ids': [],
            }

            self.db['leaderboards'].insert_one(leaderboard_data)

            return True

        else:
            print('ERROR:', leaderboard_hash, 'appears to have been deleted from Beat Saver.')
            return False

    def get_leaderboards(self, leaderboard_id_list):
        return list(self.db['leaderboards'].find({'_id': {'$in': leaderboard_id_list}}))

    def search_leaderboards(self, search):
        return list(self.db['leaderboards'].find(search))

    def create_map_pool(self, name, cover='/static/default_pool_cover.png', third_party=False):
        self.db['ranked_lists'].insert_one({
            '_id': name,
            'leaderboard_id_list': [],
            'shown_name': name,
            'third_party': third_party,
            'cover': cover,
        })

    def rank_song(self, leaderboard_id, map_pool):
        self.db['ranked_lists'].update_one({'_id': map_pool}, {'$push': {'leaderboard_id_list': leaderboard_id}})

    def get_ranked_lists(self):
        return list(self.db['ranked_lists'].find({}))

    def get_ranked_list(self, group_id):
        return self.db['ranked_lists'].find_one({'_id': group_id})

    def get_pool_ids(self):
        return [v['_id'] for v in self.db['ranked_lists'].aggregate([{'$match': {'deletedAt': None}}, {'$group': {'_id': '$_id'}}])]

print('MongoDB requires a password!')
database = HitbloqMongo(getpass())

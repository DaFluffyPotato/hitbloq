import time
from getpass import getpass
from hashlib import sha256

import pymongo

import scoresaber, beatsaver
import user
import config as old_config
from cr_formulas import *
from general import max_score
from config_loader import config

def hash_ip(ip_address):
    return sha256(ip_address.encode('utf-8')).hexdigest()

class HitbloqMongo():
    def __init__(self, password):
        self.client = pymongo.MongoClient('mongodb://' + config['mongo_username'] + ':' + password + '@' + config['mongo_host'] + ':' + config['mongo_port'] + '/?authSource=admin', connectTimeoutMS=30000, socketTimeoutMS=None, connect=False, maxPoolsize=1)
        self.db = self.client['hitbloq_com']

    def gen_new_user_id(self):
        return self.db['counters'].find_and_modify(query={'type': 'user_id'}, update={'$inc': {'count': 1}})['count']

    def get_counter(self, type):
        return self.db['counters'].find_one({'type': type})

    def inc_counter(self, counter_id, amt=1):
        self.db['counters'].update_many({'type': counter_id}, {'$inc': {'count': amt}})

    def add_user(self, user):
        self.db['users'].insert_one(user.jsonify())

    def get_all_users(self):
        return [user.User().load(user_found) for user_found in self.db['users'].find({})]

    def get_users(self, users):
        return [user.User().load(user_found) for user_found in self.db['users'].find({'_id': {'$in': users}})]

    def search_users(self, search):
        return [user.User().load(user_found) for user_found in self.db['users'].find(search)]

    def update_user(self, user, update=None):
        if update:
            self.db['users'].update_one({'_id': user.id}, update)
        else:
            self.db['users'].replace_one({'_id': user.id}, user.jsonify())

    def update_user_scores(self, user, action_id=None):
        scoresaber_api = scoresaber.ScoresaberInterface(self.db)
        new_scores = scoresaber_api.fetch_until(user.scoresaber_id, user.last_update)
        for i, score in enumerate(new_scores):
            print('adding score', i, '/', len(new_scores))
            self.add_score(user, score)
            if i % 10 == 0:
                self.set_action_progress(action_id, i / len(new_scores))

        self.update_user(user, {'$set': {'last_update': time.time()}})
        if len(new_scores):
            fresh_user = self.get_users([user.id])[0]
            self.update_user_cr_total(fresh_user)
            for map_pool_id in fresh_user.cr_totals:
                self.update_user_ranking(fresh_user, map_pool_id)

    def update_user_profile(self, user):
        scoresaber_api = scoresaber.ScoresaberInterface(self.db)


    def update_user_ranking(self, user, map_pool_id):
        if map_pool_id in user.cr_totals:
            resp = self.db['ladders'].update_one({'_id': map_pool_id, 'ladder.user': user.id}, {'$set': {'ladder.$.cr': user.cr_totals[map_pool_id]}})
            if not resp.matched_count:
                self.db['ladders'].update_one({'_id': map_pool_id}, {'$push': {'ladder': {'user': user.id, 'cr': user.cr_totals[map_pool_id]}}})
        self.sort_ladder(map_pool_id)

    def get_user_ranking(self, user, map_pool_id):
        # kinda yikes, but I'm not sure how to match just one field for indexOfArray
        if map_pool_id in user.cr_totals:
            resp = self.db['ladders'].aggregate([{'$match': {'_id': map_pool_id}}, {'$project': {'index': {'$indexOfArray': ['$ladder.user', user.id]}}}])
            return list(resp)[0]['index'] + 1
        else:
            return 0

    def get_ranking_slice(self, map_pool_id, start, end):
        return self.db['ladders'].find_one({'_id': map_pool_id}, {'ladder': {'$slice': [start, end - start]}})

    def sort_ladder(self, map_pool_id):
        self.db['ladders'].update_one({'_id': map_pool_id}, {'$push': {'ladder': {'$each': [], '$sort': {'cr': -1}}}})

    def format_score(self, user, scoresaber_json, leaderboard):
        cr_curve_data = {}
        if leaderboard['star_rating'] != {}:
            cr_curve_data = {rl['_id']: rl['cr_curve'] for rl in self.search_ranked_lists({'_id': {'$in': list(leaderboard['star_rating'])}})}
        cr_data = {}
        for pool_id in leaderboard['star_rating']:
            cr_data[pool_id] = calculate_cr(scoresaber_json['score'] / max_score(leaderboard['notes']) * 100, leaderboard['star_rating'][pool_id], cr_curve_data[pool_id])
        score_data = {
            # typo in scoresaber api. lul
            'score': scoresaber_json['unmodififiedScore'],
            'time_set': scoresaber_json['epochTime'],
            'song_id': scoresaber_json['songHash'] + '|' + scoresaber_json['difficultyRaw'],
            'cr': cr_data,
            'user': user.id,
        }
        return score_data

    def delete_scores(self, leaderboard_id, score_id_list):
        self.db['scores'].delete_many({'_id': {'$in': score_id_list}})
        self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$pull': {'score_ids': {'$in': score_id_list}}})

    def delete_user_null_pointers(self, user):
        matching_scores = set([score['_id'] for score in self.fetch_scores(user.score_ids)])
        null_pointers = set(user.score_ids) - matching_scores
        if len(null_pointers):
            print('deleting null pointers', null_pointers)
            print('(user: ' + str(user.id) + ')')
        self.db['users'].update_one({'_id': user.id}, {'$pull': {'score_ids': {'$in': list(null_pointers)}}})

    def fetch_scores(self, score_id_list):
        return self.db['scores'].find({'_id': {'$in': score_id_list}}).sort('time_set', -1)

    def replace_scores(self, scores):
        score_ids = [score['_id'] for score in scores]
        if score_ids != []:
            self.db['scores'].delete_many({'_id': {'$in': score_ids}})
            self.db['scores'].insert_many(scores)
        else:
            print('warning: no scores to replace')

    # no longer used since scores must be dynamically sorted on a per-pool basis
    def update_user_score_order(self, user):
        user.load_scores(self)
        user.scores.sort(key=lambda x: x['cr'], reverse=True)
        print(user.scores)
        score_id_list = [score['_id'] for score in user.scores]
        self.db['users'].update_one({'_id': user.id}, {'$set': {'score_ids': score_id_list}})

    def update_user_cr_total(self, user):
        user.load_scores(self)
        map_pool_ids = list(user.cr_totals)
        map_pools = self.search_ranked_lists({'_id': {'$in': map_pool_ids}})
        cr_counters = {map_pool_id : 0 for map_pool_id in map_pool_ids}
        cr_totals = {map_pool_id : 0 for map_pool_id in map_pool_ids}
        for map_pool in map_pools:
            valid_scores = [score for score in user.scores if map_pool['_id'] in score['cr']]
            valid_scores.sort(key=lambda x: x['cr'][map_pool['_id']], reverse=True)
            for score in valid_scores:
                if score['song_id'] in map_pool['leaderboard_id_list']:
                    cr_totals[map_pool['_id']] += cr_accumulation_curve(cr_counters[map_pool['_id']]) * score['cr'][map_pool['_id']]
                    cr_counters[map_pool['_id']] += 1
        for pool in cr_totals:
            user.cr_totals[pool] = cr_totals[pool]
        self.db['users'].update_one({'_id': user.id}, {'$set': {'total_cr': user.cr_totals}})

    def add_score(self, user, scoresaber_json):
        leaderboard_id = scoresaber_json['songHash'] + '|' + scoresaber_json['difficultyRaw']
        valid_leaderboard = True
        leaderboard = list(self.db['leaderboards'].find({'_id': leaderboard_id}))
        if len(leaderboard) == 0:
            leaderboard = self.create_leaderboard(leaderboard_id, scoresaber_json['songHash'])
            if not leaderboard:
                return False
        else:
            leaderboard = leaderboard[0]

        if valid_leaderboard:
            if scoresaber_json['mods'] not in ['', 'FS']:
                return False

            # delete old score data
            matching_scores = self.db['scores'].find({'user': user.id, 'song_id': scoresaber_json['songHash'] + '|' + scoresaber_json['difficultyRaw']})
            matching_scores = [score['_id'] for score in matching_scores]
            self.delete_scores(leaderboard_id, matching_scores)

            # add new score
            score_json = self.format_score(user, scoresaber_json, leaderboard)
            mongo_response = self.db['scores'].insert_one(score_json)
            inserted_id = mongo_response.inserted_id
            self.update_user(user, {'$push': {'score_ids': inserted_id}})
            self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$push': {'score_ids': inserted_id}})
            self.delete_user_null_pointers(user)
            self.refresh_score_order(leaderboard_id)
            return True

    def delete_user_scores(self, user_id):
        score_list = list(self.db['scores'].find({'user': user_id}))
        score_ids = [score['_id'] for score in score_list]

        for score in score_list:
            self.db['leaderboards'].update_one({'_id': score['song_id']}, {'$pull': {'score_ids': score['_id']}})

        self.db['scores'].delete_many({'_id': {'$in': score_ids}})

    def delete_user(self, user_id):
        self.delete_user_scores(user_id)
        for ladder in self.db['ladders'].find({}):
            for user in ladder['ladder']:
                if 'user' not in user:
                    print('user with no user?')
                    ladder['ladder'].remove(user)
                    continue
                if user['user'] == user_id:
                    print('removed', user, 'from', ladder['_id'])
                    ladder['ladder'].remove(user)
                    break
            self.db['ladders'].update_one({'_id': ladder['_id']}, {'$set': {'ladder': ladder['ladder']}})
        self.db['users'].delete_one({'_id': user_id})
        print('deleted user', user_id)

    def refresh_score_order(self, leaderboard_id):
        leaderboard_data = self.db['leaderboards'].find_one({'_id': leaderboard_id})
        new_score_order = [score['_id'] for score in self.fetch_scores(leaderboard_data['score_ids']).sort('score', -1)]
        self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$set': {'score_ids': new_score_order}})

    def get_full_ranked_list(self):
        map_pools = self.get_ranked_lists()
        ranked_maps = []
        for pool in map_pools:
            ranked_maps += pool['leaderboard_id_list']
        ranked_maps = list(set(ranked_maps))
        return ranked_maps

    def create_leaderboard(self, leaderboard_id, leaderboard_hash, transfer=False):
        print('Creating leaderboard:', leaderboard_id)

        ranked_maps = self.get_full_ranked_list()

        new_scores = []

        # create dummy leaderboard
        if leaderboard_id not in ranked_maps:
            leaderboard_data = {
                '_id': leaderboard_id,
                'key': None,
                'cover': None,
                'name': None,
                'sub_name': None,
                'artist': None,
                'mapper': None,
                'bpm': -1,
                'difficulty_settings': leaderboard_id.split('|')[-1],
                'difficulty': None,
                'characteristic': None,
                'duration': -1,
                'difficulty_duration': -1,
                'length': -1,
                'njs': -1,
                'bombs': -1,
                'notes': 99999,
                'obstacles': -1,
                'hash': leaderboard_hash,
                'score_ids': [],
                'star_rating': {},
                'forced_star_rating': {},
            }

            self.db['leaderboards'].insert_one(leaderboard_data)

            return leaderboard_data

        elif transfer:
            print('transferring scores on leaderboard', leaderboard_id)
            old_leaderboard_data = self.db['leaderboards'].find_one({'_id': leaderboard_id})
            new_scores = old_leaderboard_data['score_ids']
            print(len(new_scores), 'scores being transferred...')

        # remove old instances
        self.db['leaderboards'].delete_many({'_id': leaderboard_id})

        leaderboard_difficulty = leaderboard_id.split('|')[-1]

        beatsaver_api = beatsaver.BeatSaverInterface()
        beatsaver_data = beatsaver_api.lookup_song_hash(leaderboard_hash)

        if beatsaver_data:
            characteristic = leaderboard_difficulty.split('_')[-1]
            try:
                characteristic = old_config.CHARACTERISTIC_CONVERSION[characteristic]
            except KeyError:
                print('ERROR:', characteristic, 'is not a known characteristic.')
                return None

            difficulty = leaderboard_difficulty.split('_')[1]
            difficulty = old_config.DIFFICULTY_CONVERSION[difficulty]

            # get the correct difficulty data based on characteristic and difficulty
            try:
                difficulty_data = [c['difficulties'] for c in beatsaver_data['metadata']['characteristics'] if c['name'] == characteristic][0][difficulty]
                if difficulty_data == None:
                    print('ERROR: the', difficulty, 'difficulty may have been deleted from Beat Saver...')
                    return None
            except IndexError:
                print('ERROR: the', characteristic, 'characteristic may have been deleted from Beat Saver...')
                return None

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
                'score_ids': new_scores,
                'star_rating': {},
                'forced_star_rating': {},
            }

            self.db['leaderboards'].insert_one(leaderboard_data)

            return leaderboard_data

        else:
            print('ERROR:', leaderboard_hash, 'appears to have been deleted from Beat Saver.')
            return None

    def get_leaderboards(self, leaderboard_id_list):
        return list(self.db['leaderboards'].find({'_id': {'$in': leaderboard_id_list}}))

    def search_leaderboards(self, search):
        return list(self.db['leaderboards'].find(search))

    def update_leaderboard_data(self, leaderboard_id, updates):
        self.db['leaderboards'].update({'_id': leaderboard_id}, updates)

    def create_map_pool(self, name, cover='/static/default_pool_cover.png', third_party=False):
        self.db['ranked_lists'].insert_one({
            '_id': name,
            'leaderboard_id_list': [],
            'shown_name': name,
            'third_party': third_party,
            'cover': cover,
            'cr_curve': {'type': 'basic'},
            'player_count': 0,
        })
        self.db['ladders'].insert_one({
            '_id': name,
            'ladder': [],
        })
        if not third_party:
            self.db['users'].update_many({}, {'$set': {'total_cr.' + name : 0}})

    def delete_map_pool(self, name):
        self.db['users'].update_many({}, {'$unset': {'rank_history.' + name: 1, 'max_rank.' + name: 1, 'total_cr.' + name: 1}})
        self.db['leaderboards'].update_many({}, {'$unset': {'star_rating.' + name: 1, 'forced_star_rating.' + name: 1}})
        self.db['scores'].update_many({}, {'$unset': {'cr.' + name: 1}})
        self.db['ladders'].delete_one({'_id': name})
        self.db['ranked_lists'].delete_one({'_id': name})
        print('successfully deleted map pool:', name)

    def unrank_song(self, leaderboard_id, map_pool):
        self.db['ranked_lists'].update_one({'_id': map_pool}, {'$pull': {'leaderboard_id_list': leaderboard_id}})

        current_leaderboard = self.db['leaderboards'].find_one({'_id': leaderboard_id})
        if current_leaderboard:
            print('found leaderboard')
            self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$unset': {'star_rating.' + map_pool: 1}})

            scores = list(self.fetch_scores(current_leaderboard['score_ids']))
            for score in scores:
                if map_pool in score['cr']:
                    del score['cr'][map_pool]
            print('replacing', len(scores), 'scores')
            self.replace_scores(scores)

    def rank_song(self, leaderboard_id, map_pool):
        # ensure that it wasn't previously added
        self.db['ranked_lists'].update_one({'_id': map_pool}, {'$pull': {'leaderboard_id_list': leaderboard_id}})

        self.db['ranked_lists'].update_one({'_id': map_pool}, {'$push': {'leaderboard_id_list': leaderboard_id}})
        current_leaderboard = self.db['leaderboards'].find_one({'_id': leaderboard_id})
        if not current_leaderboard:
            self.create_leaderboard(leaderboard_id, leaderboard_id.split('|')[0])
            current_leaderboard = self.db['leaderboards'].find_one({'_id': leaderboard_id})
        elif current_leaderboard['key'] == None:
            self.create_leaderboard(leaderboard_id, leaderboard_id.split('|')[0], True)
            current_leaderboard = self.db['leaderboards'].find_one({'_id': leaderboard_id})
        self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$set': {'star_rating.' + map_pool: 0}})
        scores = list(self.fetch_scores(current_leaderboard['score_ids']))
        for score in scores:
            score['cr'][map_pool] = 0
        self.replace_scores(scores)

    def get_ranked_lists(self):
        return list(self.db['ranked_lists'].find({}))

    def search_ranked_lists(self, search):
        return list(self.db['ranked_lists'].find(search))

    def get_ranked_list(self, group_id):
        return self.db['ranked_lists'].find_one({'_id': group_id})

    def get_pool_ids(self, allow_third_party=True):
        if allow_third_party:
            return [v['_id'] for v in self.db['ranked_lists'].aggregate([{'$match': {'deletedAt': None}}, {'$group': {'_id': '$_id'}}])]
        else:
            return [v['_id'] for v in self.db['ranked_lists'].aggregate([{'$match': {'deletedAt': None, 'third_party': False}}, {'$group': {'_id': '$_id'}}])]

    def add_action(self, action):
        action['progress'] = 0
        action['time'] = time.time()
        self.db['actions'].insert_one(action)

    def add_actions(self, actions):
        for action in actions:
            action['progress'] = 0
            action['time'] = time.time()
        self.db['actions'].insert_many(actions)

    def get_actions(self):
        return self.db['actions'].find({}).sort([('time', pymongo.ASCENDING)])

    def get_next_action(self):
        try:
            return self.get_actions().limit(1).next()
        except StopIteration:
            return None

    def clear_action(self, action_id):
        self.db['actions'].delete_one({'_id': action_id})

    def set_action_progress(self, action_id, progress):
        if action_id:
            self.db['actions'].update_one({'_id': action_id}, {'$set': {'progress': progress}})

    def get_rate_limits(self, ip_address):
        ip_hash = hash_ip(ip_address)
        ratelimits = self.db['ratelimits'].find_one({'_id': ip_hash})
        if not ratelimits:
            ratelimits = {
                '_id': ip_hash,
                'user_additions': 0,
            }
            self.db['ratelimits'].insert_one(ratelimits)
        return ratelimits

    def ratelimit_add(self, ip_address, field):
        ip_hash = hash_ip(ip_address)
        self.db['ratelimits'].update_one({'_id': ip_hash}, {'$inc': {field: 1}})

    def set_pool_curve(self, pool_id, curve_data):
        self.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'cr_curve': curve_data}})

    def update_rank_histories(self, pool_id, action_id=None):
        ranked_ladder = self.db['ladders'].find_one({'_id': pool_id})['ladder']
        # this will need to be bundled into one request somehow later on
        for rank, user in enumerate(ranked_ladder):
            self.db['users'].update_one({'_id': user['user']}, {'$push': {'rank_history.' + pool_id: {'$each': [rank + 1], '$slice': -60}}, '$min': {'max_rank.' + pool_id: rank + 1}})
            if action_id:
                if rank % 20 == 0:
                    self.set_action_progress(action_id, rank / len(ranked_ladder))

print('MongoDB requires a password!')
database = HitbloqMongo(getpass())

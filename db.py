import time
from getpass import getpass
from hashlib import sha256

import pymongo
from pymongo import UpdateOne
from bson.objectid import ObjectId

import scoresaber, beatleader, beatsaver
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

    def get_all_user_ids(self):
        return [user['_id'] for user in database.db['users'].find({}, {'_id': 1}).hint('_id_')]

    def get_all_users(self):
        return [user.User().load(user_found) for user_found in self.db['users'].find({})]

    def get_users(self, users, pool_id=None):
        if pool_id:
            aggregation_results = database.db['users'].aggregate([
                {'$match': {'_id': {'$in': users}}},
                {'$lookup': {'from': 'za_pool_users_' + pool_id, 'localField': '_id', 'foreignField': '_id', 'as': 'pool_stats'}}
                ])

            return [user.User().load(user_found, pool_id=pool_id) for user_found in aggregation_results]
        else:
            return [user.User().load(user_found) for user_found in self.db['users'].find({'_id': {'$in': users}})]

    def search_users(self, search):
        return [user.User().load(user_found) for user_found in self.db['users'].find(search)]

    def update_user(self, user, update=None):
        if update:
            self.db['users'].update_one({'_id': user.id}, update)
        else:
            self.db['users'].replace_one({'_id': user.id}, user.jsonify())

    def update_user_scores(self, user, action_id=None, queue_id=0):
        new_scores = []
        if user.valid_profiles['ss']:
            scoresaber_api = scoresaber.ScoresaberInterface(self.db, queue_id=queue_id)
            new_scores += scoresaber_api.fetch_until(user.scoresaber_id, user.last_update)
        if user.valid_profiles['bl']:
            beatleader_api = beatleader.BeatLeaderInterface()
            new_scores += beatleader_api.fetch_until(user.scoresaber_id, user.last_update)
        new_score_ids = []
        for i, score in enumerate(new_scores):
            print('adding score', i, '/', len(new_scores))
            new_score_id = self.add_score(user, score)
            new_score_ids.append(new_score_id)
            if i % 10 == 0:
                self.set_action_progress(action_id, i / len(new_scores))

        if len(new_scores):
            fresh_user = self.get_users([user.id])[0]
            self.update_user_cr_total(fresh_user, score_ids=new_score_ids)

        self.update_user(user, {'$set': {'last_update': time.time()}})

    def update_user_profile(self, user):
        scoresaber_api = scoresaber.ScoresaberInterface(self.db)

    def get_user_ranking(self, user, map_pool_id):
        if map_pool_id in user.cr_totals:
            cr_total = user.cr_totals[map_pool_id]

            rank = self.db['za_pool_users_' + map_pool_id].find({'cr_total': {'$gt': cr_total}}).sort('cr_total', -1).count() + 1

            return rank

        return 0

    def get_ranking_slice(self, map_pool_id, start, end):
        ladder_data = {
            '_id': map_pool_id,
            'ladder': [],
        }

        for user in self.db['za_pool_users_' + map_pool_id].find({}).sort('cr_total', -1).skip(start).limit(end - start):
            ladder_data['ladder'].append({'user': user['_id'], 'cr': user['cr_total']})

        return ladder_data

    def format_score(self, user, scoresaber_json, leaderboard):
        cr_curve_data = {}
        if leaderboard['star_rating'] != {}:
            cr_curve_data = {rl['_id']: rl['cr_curve'] for rl in self.search_ranked_lists({'_id': {'$in': list(leaderboard['star_rating'])}})}
        cr_data = {}
        for pool_id in leaderboard['star_rating']:
            cr_data[pool_id] = calculate_cr(scoresaber_json['score']['modifiedScore'] / max_score(leaderboard['notes']) * 100, leaderboard['star_rating'][pool_id], cr_curve_data[pool_id])
        score_data = {
            'score': scoresaber_json['score']['modifiedScore'],
            'max_combo': scoresaber_json['score']['maxCombo'],
            'missed_notes': scoresaber_json['score']['missedNotes'],
            'bad_cuts': scoresaber_json['score']['badCuts'],
            'hmd': scoresaber_json['score']['hmd'],
            'time_set': scoresaber_json['score']['epochTime'],
            'song_id': scoresaber_json['leaderboard']['songHash'] + '|' + scoresaber_json['leaderboard']['difficulty']['difficultyRaw'],
            'cr': cr_data,
            'user': user.id,
        }
        return score_data

    def delete_scores(self, leaderboard_id, score_id_list):
        self.db['scores'].delete_many({'_id': {'$in': score_id_list}})

    def fetch_scores(self, score_id_list):
        return self.db['scores'].find({'_id': {'$in': score_id_list}}).sort('time_set', -1)

    def replace_scores(self, scores):
        score_ids = [score['_id'] for score in scores]
        if score_ids != []:
            self.db['scores'].delete_many({'_id': {'$in': score_ids}})
            success = False
            for i in range(5):
                self.db['scores'].insert_many(scores)
                if self.db['scores'].find({'_id': {'$in': score_ids}}).count() == len(scores):
                    success = True
                    break
                else:
                    new_notification('warning', 'failed to detect inserted scores for score replacement')
            if not success:
                new_notification('critical_error', 'failed to detect inserted scores for score replacement', data=scores)
        else:
            print('warning: no scores to replace')

    def update_user_cr_total(self, user, score_ids=[]):
        user.load_scores(self)
        map_pool_ids = self.get_ranked_list_ids()
        map_pools = self.search_ranked_lists({'_id': {'$in': map_pool_ids}})
        cr_counters = {map_pool_id : 0 for map_pool_id in map_pool_ids}
        cr_totals = {map_pool_id : 0 for map_pool_id in map_pool_ids}
        changed_totals = []
        for map_pool in map_pools:
            valid_scores = [score for score in user.scores if map_pool['_id'] in score['cr']]
            valid_scores.sort(key=lambda x: x['cr'][map_pool['_id']], reverse=True)
            for score in valid_scores:
                if score['song_id'] in map_pool['leaderboard_id_list']:
                    cr_totals[map_pool['_id']] += cr_accumulation_curve(cr_counters[map_pool['_id']], map_pool['accumulation_constant']) * score['cr'][map_pool['_id']]
                    cr_counters[map_pool['_id']] += 1

                    if score['_id'] in score_ids:
                        changed_totals.append(map_pool['_id'])

        for pool in cr_totals:
            user.cr_totals[pool] = cr_totals[pool]

        for pool_id in changed_totals:
            self.db['za_pool_users_' + pool_id].update_one({'_id': user.id}, {'$set': {'cr_total': user.cr_totals[pool_id]}})
        user.unload_scores()

    def add_score(self, user, scoresaber_json):
        leaderboard_id = scoresaber_json['leaderboard']['songHash'] + '|' + scoresaber_json['leaderboard']['difficulty']['difficultyRaw']
        valid_leaderboard = True
        leaderboard = list(self.db['leaderboards'].find({'_id': leaderboard_id}))
        if len(leaderboard) == 0:
            leaderboard = self.create_leaderboard(leaderboard_id, scoresaber_json['leaderboard']['songHash'])
            if not leaderboard:
                return False
        else:
            leaderboard = leaderboard[0]

        if valid_leaderboard:
            if scoresaber_json['score']['modifiers'] not in ['']:
                return False

            # fetch old score data
            matching_scores = list(self.db['scores'].find({'user': user.id, 'song_id': scoresaber_json['leaderboard']['songHash'] + '|' + scoresaber_json['leaderboard']['difficulty']['difficultyRaw']}))

            # ignore score if the old scores are better
            for score in matching_scores:
                if score['score'] > scoresaber_json['score']['modifiedScore']:
                    return False

            # delete old scores
            matching_scores = [score['_id'] for score in matching_scores]
            self.delete_scores(leaderboard_id, matching_scores)

            # add new score
            score_json = self.format_score(user, scoresaber_json, leaderboard)
            mongo_response = self.db['scores'].insert_one(score_json)
            inserted_id = mongo_response.inserted_id
            return inserted_id

    def delete_user_scores(self, user_id):
        score_list = list(self.db['scores'].find({'user': user_id}))
        score_ids = [score['_id'] for score in score_list]

        self.db['scores'].delete_many({'_id': {'$in': score_ids}})

    def delete_user_pool_info(self, user_id):
        for pool in self.get_pool_ids():
            self.db['za_pool_users_' + pool].delete_one({'_id': user_id})

    def delete_user(self, user_id):
        self.delete_user_scores(user_id)
        self.delete_user_pool_info(user_id)
        self.db['users'].delete_one({'_id': user_id})
        print('deleted user', user_id)

    def ban_user(self, user_id):
        user = self.db['users'].find_one({'_id': user_id})
        self.db['bans'].insert_one({'_id': user_id, 'scoresaber_id': user['scoresaber_id'], 'username': user['username'], 'time': time.time()})
        self.delete_user(user_id)

    def get_full_ranked_list(self):
        map_pools = self.get_ranked_lists()
        ranked_maps = []
        for pool in map_pools:
            ranked_maps += pool['leaderboard_id_list']
        ranked_maps = list(set(ranked_maps))
        return ranked_maps

    def create_leaderboard(self, leaderboard_id, leaderboard_hash, transfer=False):
        leaderboard_hash = leaderboard_hash.upper()
        try:
            leaderboard_id = leaderboard_id.split('|')[0].upper() + '|' + leaderboard_id.split('|')[1]
        except:
            print('invalid leaderboard id:', leaderboard_id)
            return

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
                'max_score': 9999999,
                'obstacles': -1,
                'hash': leaderboard_hash,
                'star_rating': {},
                'forced_star_rating': {},
            }

            self.db['leaderboards'].insert_one(leaderboard_data)

            return leaderboard_data

        elif transfer:
            print('transferring data from leaderboard', leaderboard_id)
            old_leaderboard_data = self.db['leaderboards'].find_one({'_id': leaderboard_id})

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
            difficulty_data = beatsaver_api.get_diff_data(beatsaver_data, difficulty, characteristic)
            if not difficulty_data:
                print('ERROR: the', difficulty, characteristic, 'version of song', leaderboard_hash, 'may have been deleted.')
                return None

            version_data = beatsaver_data['versions'][0]

            leaderboard_data = {
                '_id': leaderboard_id,
                'key': beatsaver_data['id'],
                'cover': version_data['coverURL'],
                'name': beatsaver_data['metadata']['songName'],
                'sub_name': beatsaver_data['metadata']['songSubName'],
                'artist': beatsaver_data['metadata']['songAuthorName'],
                'mapper': beatsaver_data['metadata']['levelAuthorName'],
                'bpm': beatsaver_data['metadata']['bpm'],
                'difficulty_settings': leaderboard_id.split('|')[-1],
                'difficulty': difficulty,
                'characteristic': characteristic,
                'duration': beatsaver_data['metadata']['duration'],
                'difficulty_duration': difficulty_data['seconds'],
                'length': difficulty_data['length'],
                'njs': difficulty_data['njs'],
                'bombs': difficulty_data['bombs'],
                'notes': difficulty_data['notes'],
                'max_score': difficulty_data['maxScore'],
                'obstacles': difficulty_data['obstacles'],
                'hash': leaderboard_hash,
                'star_rating': old_leaderboard_data['star_rating'] if transfer else {},
                'forced_star_rating': old_leaderboard_data['forced_star_rating'] if transfer else {},
            }

            # remove old instances
            print('removed old scores')
            self.db['leaderboards'].delete_many({'_id': leaderboard_id})
            # add new data
            print('added new data')
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
        map_pool_data = {
            '_id': name,
            'leaderboard_id_list': [],
            'shown_name': name,
            'banner_title_hide': False,
            'third_party': third_party,
            'cover': cover,
            'playlist_cover': None,
            'cr_curve': {'type': 'basic'},
            'player_count': 0,
            'priority': 0,
            'accumulation_constant': 0.94,
            'owners': [],
            'needs_cr_total_recalc': False,
            'force_recalc': False,
            'short_description': None,
            'long_description': '',
            'date_created': time.time(),
            'views': 0,
        }

        print('creating map pool:')
        print(map_pool_data)

        self.db['ranked_lists'].insert_one(map_pool_data)

        bulk_insert = []
        database.db['za_pool_users_' + name].create_index([('cr_total', pymongo.DESCENDING)])

        i = 0
        for user in self.db['users'].find({}, {'_id': 1}):
            user_pool_data = {
                '_id': user['_id'],
                'cr_total': 0,
                'rank_history': [],
                'max_rank': 999999999,
            }
            bulk_insert.append(user_pool_data)
            if i % 5000 == 4999:
                self.db['za_pool_users_' + name].insert_many(bulk_insert)
                bulk_insert = []
            i += 1

        if len(bulk_insert):
            self.db['za_pool_users_' + name].insert_many(bulk_insert)

    def set_pool_owners(self, map_pool, owners):
        self.db['ranked_lists'].update_one({'_id': map_pool}, {'$set': {'owners': owners}})

    def is_pool_owner(self, map_pool, discord_id):
        owners = self.db['ranked_lists'].find_one({'_id': map_pool})
        if owners:
            if discord_id in owners['owners']:
                return True
            else:
                return False
        else:
            return False

    def delete_map_pool(self, name):
        self.db['leaderboards'].update_many({}, {'$unset': {'star_rating.' + name: 1, 'forced_star_rating.' + name: 1}})
        self.db['scores'].update_many({}, {'$unset': {'cr.' + name: 1}})
        self.db['ranked_lists'].delete_one({'_id': name})
        self.db['za_pool_users_' + name].drop()
        print('successfully deleted map pool:', name)

    def copy_map_pool(self, src, new):
        self.db['leaderboards'].update_many({'star_rating.' + src: {'$exists': True}}, [{'$set': {'star_rating.' + new: '$star_rating.' + src, 'forced_star_rating.' + new: '$forced_star_rating.' + src}}])
        self.db['scores'].update_many({'cr.' + src: {'$exists': True}}, [{'$set': {'cr.' + new: '$cr.' + src}}])
        old_ranked_list = self.db['ranked_lists'].find_one({'_id': src})
        old_ranked_list['_id'] = new
        self.db['ranked_lists'].insert_one(old_ranked_list)
        self.db['za_pool_users_' + src].aggregate([{'$out': 'za_pool_users_' + new}])
        self.db['pool_interest'].update_many({'pools_viewed.' + src: {'$exists': True}}, [{'$set': {'pools_viewed.' + new: '$pools_viewed.' + src}}])
        print('successfully copied map pool', src, 'to', new)

    def create_pool_reference(self, src, target):
        self.db['pool_references'].insert_one({'_id': src, 'target': target})

    def unrank_song(self, leaderboard_id, map_pool):
        self.db['ranked_lists'].update_one({'_id': map_pool}, {'$pull': {'leaderboard_id_list': leaderboard_id}})

        current_leaderboard = self.db['leaderboards'].find_one({'_id': leaderboard_id})
        if current_leaderboard:
            print('found leaderboard')
            self.db['leaderboards'].update_one({'_id': leaderboard_id}, {'$unset': {'star_rating.' + map_pool: 1}})

            scores = list(database.db['scores'].find({'song_id': leaderboard_id}))
            for score in scores:
                if map_pool in score['cr']:
                    del score['cr'][map_pool]
            print('replacing', len(scores), 'scores')
            self.replace_scores(scores)

            self.db['pool_feeds'].insert_one({
                'pool': map_pool,
                'category': 'ranking',
                'status': 'unranked',
                'leaderboard_id': leaderboard_id,
                'time': time.time(),
            })

    def rank_song(self, leaderboard_id, map_pool):
        leaderboard_id = leaderboard_id.split('|')[0].upper() + '|' + leaderboard_id.split('|')[1]
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
        scores = list(self.db['scores'].find({'song_id': leaderboard_id}))
        for score in scores:
            score['cr'][map_pool] = 0
        self.replace_scores(scores)

        self.db['pool_feeds'].insert_one({
            'pool': map_pool,
            'category': 'ranking',
            'status': 'ranked',
            'leaderboard_id': leaderboard_id,
            'time': time.time(),
        })

    def reimport_song(self, leaderboard_id):
        current_leaderboard = self.db['leaderboards'].find_one({'_id': leaderboard_id})
        if current_leaderboard and current_leaderboard['key']:
            self.create_leaderboard(leaderboard_id, leaderboard_id.split('|')[0], transfer=True)
            print('reimporting', leaderboard_id)

    def get_ranked_lists(self):
        return list(self.db['ranked_lists'].find({}).sort('priority', -1))

    def get_ranked_list_ids(self):
        return [rl['_id'] for rl in database.db['ranked_lists'].find({}, {'_id': 1}).hint('_id_')]

    def search_ranked_lists(self, search):
        return list(self.db['ranked_lists'].find(search))

    def get_ranked_list(self, group_id):
        return self.db['ranked_lists'].find_one({'_id': group_id})

    def get_pool_ids(self, allow_third_party=True):
        if allow_third_party:
            return [v['_id'] for v in self.db['ranked_lists'].aggregate([{'$match': {'deletedAt': None}}, {'$group': {'_id': '$_id'}}])]
        else:
            return [v['_id'] for v in self.db['ranked_lists'].aggregate([{'$match': {'deletedAt': None, 'third_party': False}}, {'$group': {'_id': '$_id'}}])]

    def add_action(self, action, queue_id=0):
        action['progress'] = 0
        action['time'] = time.time()
        action['queue_id'] = queue_id
        mongo_response = self.db['actions'].insert_one(action)
        inserted_id = str(mongo_response.inserted_id)
        return inserted_id

    def action_exists(self, action_id):
        return bool(self.db['actions'].find_one({'_id': ObjectId(action_id)}))

    def add_actions(self, actions, queue_id=0):
        for action in actions:
            action['progress'] = 0
            action['time'] = time.time()
            action['queue_id'] = queue_id
        self.db['actions'].insert_many(actions)

    def get_actions(self, queue_id=0):
        if queue_id == -1:
            return self.db['actions'].find({}).sort([('time', pymongo.ASCENDING)])
        else:
            return self.db['actions'].find({'queue_id': queue_id}).sort([('time', pymongo.ASCENDING)])

    def get_next_action(self, queue_id=0):
        try:
            return self.get_actions(queue_id).limit(1).next()
        except StopIteration:
            return None

    def clear_action(self, action_id):
        self.db['actions'].delete_one({'_id': action_id})

    def set_action_progress(self, action_id, progress):
        if action_id:
            self.db['actions'].update_one({'_id': action_id}, {'$set': {'progress': progress}})

    def get_rate_limits(self, ip_address, hash=True):
        if hash:
            ip_hash = hash_ip(ip_address)
        else:
            ip_hash = ip_address
        ratelimits = self.db['ratelimits'].find_one({'_id': ip_hash})
        if not ratelimits:
            ratelimits = {
                '_id': ip_hash,
                'user_additions': 0,
                'pools_created': 0,
            }
            self.db['ratelimits'].insert_one(ratelimits)
        return ratelimits

    def ratelimit_add(self, ip_address, field, hash=True):
        if hash:
            ip_hash = hash_ip(ip_address)
        else:
            ip_hash = ip_address
        self.db['ratelimits'].update_one({'_id': ip_hash}, {'$inc': {field: 1}})

    def log_interest(self, ip_address, pool_id):
        if (pool_id.find('.') != -1) or (pool_id.find('$') != -1):
            return
        update_res = self.db['ranked_lists'].update_one({'_id': pool_id}, {'$inc': {'views': 1}})
        if update_res.matched_count:
            self.db['pool_interest'].update_one({'_id': hash_ip(ip_address)}, {'$set': {'pools_viewed.' + pool_id: time.time()}}, upsert=True)

    def calculate_pool_popularity(self):
        POOL_INTEREST_CYCLE = 60 * 60 * 24 * 30 # 30 day cycle
        interest_log = list(self.db['pool_interest'].find({}))

        current_time = time.time()

        pool_popularity = {}

        for i, user in sorted(enumerate(interest_log), reverse=True):
            for pool_id in list(user['pools_viewed']):
                if user['pools_viewed'][pool_id] > current_time - POOL_INTEREST_CYCLE:
                    if pool_id not in pool_popularity:
                        pool_popularity[pool_id] = 0
                    pool_popularity[pool_id] += 1
                # TODO add mechanism to delete old data

        for pool_id in self.get_pool_ids():
            if pool_id not in pool_popularity:
                priority = 0
            else:
                priority = pool_popularity[pool_id]
            self.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'priority': priority}})

        return pool_popularity

    def set_pool_curve(self, pool_id, curve_data):
        self.db['ranked_lists'].update_one({'_id': pool_id}, {'$set': {'cr_curve': curve_data, 'force_recalc': True}})

    def update_rank_histories(self, pool_id, action_id=None):
        ranked_ladder = [user['_id'] for user in self.db['za_pool_users_' + pool_id].find({}, {'_id': 1, 'cr_total': 1}).sort('cr_total', -1)]
        # this will need to be bundled into one request somehow later on
        for rank, user in enumerate(ranked_ladder):
            self.db['users'].update_one({'_id': user}, {'$push': {'rank_history.' + pool_id: {'$each': [rank + 1], '$slice': -60}}, '$min': {'max_rank.' + pool_id: rank + 1}})
            self.db['za_pool_users_' + pool_id].update_one({'_id': user}, {'$push': {'rank_history': {'$each': [rank + 1], '$slice': -60}}, '$min': {'max_rank': rank + 1}})

            if action_id:
                if rank % 200 == 0:
                    self.set_action_progress(action_id, rank / len(ranked_ladder))

    def create_badge(self, badge_id, description):
        self.db['badges'].update_one({'_id': badge_id}, {'$set': {'description': description}}, upsert=True)

    def give_badge(self, user_id, badge_id):
        self.db['users'].update_one({'_id': user_id}, {'$push': {'badges': badge_id}})

    def update_discord_tags(self, users):
        for user in users:
            self.db['discord_users'].update_one({'_id': user}, {'$set': {'tag': users[user]}}, upsert=True)

    def link_discord_account(self, discord_id, hitbloq_id):
        old_record = self.db['discord_users'].find_one({'_id': discord_id})
        if (not old_record) or ('user_id' in old_record):
            return False

        self.db['discord_users'].update_one({'_id': discord_id}, {'$set': {'user_id': hitbloq_id}})
        return True

    def get_linked_account(self, discord_id):
        discord_info = self.db['discord_users'].find_one({'_id': discord_id})
        if 'user_id' in discord_info:
            return discord_info['user_id']
        else:
            return -1

    def get_discord_users(self, users):
        return list(self.db['discord_users'].find({'_id': {'$in': users}}))

    def register_request(self, category='api', user_agent=None, ip=None, request_path='unknown'):
        if type(user_agent) == str:
            user_agent_base = user_agent.split(' ')[0]
            user_agent_name = user_agent_base.split('/')[0]
            user_agent_ver = user_agent_base.split('/')[1] if len(user_agent_base.split('/')) > 1 else '1.0'
        else:
            user_agent_base = 'unknown'
            user_agent_name = 'unknown'
            user_agent_ver = 'unknown'

        bulk_ops = []

        if category == 'website':
            bulk_ops.append(UpdateOne({'type': 'views'}, {'$inc': {'count': 1}}, upsert=True))
        else:
            bulk_ops.append(UpdateOne({'type': 'api_reqs'}, {'$inc': {'count': 1}}, upsert=True))
            bulk_ops.append(UpdateOne({'_id': 'api_endpoint_' + request_path, 'type': 'api_endpoint_unique'}, {'$inc': {'count': 1}}, upsert=True))

        bulk_ops.append(UpdateOne({'_id': 'ua_' + user_agent_name, 'type': 'user_agent_reqs'}, {'$inc': {'count': 1}}, upsert=True))
        self.db['counters'].bulk_write(bulk_ops)

    def new_notification(self, category, content, data=None):
        self.db['admin_notifications'].insert_one({
            'time': time.time(),
            'category': category,
            'content': content,
            'read': False,
            'data': data,
        })

    def fetch_notifications(self):
        notifications = list(self.db['admin_notifications'].find({'read': False}))
        self.db['admin_notifications'].update_many({}, {'$set': {'read': True}})
        return notifications

    def action_queue_status(self):
        queue_list = [0, 1, 2]
        busy_queues = self.db['actions'].distinct('queue_id')
        queue_statuses = {queue_id : queue_id in busy_queues for queue_id in queue_list}
        return queue_statuses

print('MongoDB requires a password!')
database = HitbloqMongo(getpass())

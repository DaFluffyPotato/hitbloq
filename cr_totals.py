import time

from pymongo import UpdateOne

from db import database
from cr_formulas import cr_accumulation_curve

class BulkCRTotalUpdate:
    def __init__(self, db, debug=True):
        self.db = db
        self.debug = debug

    def safe_bulk_update_cr_totals(self, users, pools, all_users=False, all_pools=False):
        if len(users) > 1000:
            all_users = False

        i = 0
        while len(users):
            if self.debug:
                print('batch', i)

            user_batch = users[:1000]
            users = users[1000:]
            self.bulk_update_cr_totals(user_batch, pools, all_users=all_users, all_pools=all_pools)

            i += 1

    def bulk_update_cr_totals(self, users, pools, all_users=False, all_pools=False):
        for pool in pools:
            self.db['ranked_lists'].update_one({'_id': pool}, {'$set': {'player_count': self.db['za_pool_users_' + pool].find({'cr_total': {'$gt': 0}}).count()}})
        leaderboard_ids = {}
        accumulation_constants = {}

        # shortcut queries to improve performance
        if all_pools:
            pool_query = {}
        else:
            pool_query = {'_id': {'$in': pools}}

        for pool in self.db['ranked_lists'].find(pool_query, {'leaderboard_id_list': 1, 'accumulation_constant': 1}):
            accumulation_constants[pool['_id']] = pool['accumulation_constant']
            for leaderboard_id in pool['leaderboard_id_list']:
                if leaderboard_id not in leaderboard_ids:
                    leaderboard_ids[leaderboard_id] = [pool['_id']]
                else:
                    leaderboard_ids[leaderboard_id].append(pool['_id'])

        if all_users:
            score_query = {'song_id': {'$in': list(leaderboard_ids)}}
        else:
            score_query = {'user': {'$in': users}, 'song_id': {'$in': list(leaderboard_ids)}}

        scores = self.db['scores'].find(score_query)

        cr_counters = {user : {pool : 0 for pool in pools} for user in users}
        cr_totals = {user : {pool : 0 for pool in pools} for user in users}
        user_scores = {user: {pool : [] for pool in pools} for user in users}

        for score in scores:
            for pool in leaderboard_ids[score['song_id']]:
                user_scores[score['user']][pool].append(score['cr'][pool])


        bulk_ops = []
        pool_bulk_ops = {pool : [] for pool in pools}

        # add up CR
        for user in users:
            for pool in pools:
                user_scores[user][pool].sort(reverse=True)

                for score in user_scores[user][pool]:
                    cr_totals[user][pool] += cr_accumulation_curve(cr_counters[user][pool], accumulation_constants[pool]) * score
                    cr_counters[user][pool] += 1

                # the [user][pool] result is complete at this point
                bulk_ops.append(UpdateOne({'_id': user}, {'$set': {'total_cr.' + pool: cr_totals[user][pool]}}))
                pool_bulk_ops[pool].append(UpdateOne({'_id': user}, {'$set': {'cr_total': cr_totals[user][pool]}}))

        self.db['users'].bulk_write(bulk_ops)
        for pool in pool_bulk_ops:
            if len(pool_bulk_ops[pool]):
                self.db['za_pool_users_' + pool].bulk_write(pool_bulk_ops[pool])

while True:
    update_list = []
    for pool in database.db['ranked_lists'].find({}, {'needs_cr_total_recalc': 1}):
        if pool['needs_cr_total_recalc']:
            update_list.append(pool['_id'])

    if len(update_list):
        print('updating totals for pools:')
        print(update_list)
        BulkCRTotalUpdate(database.db).safe_bulk_update_cr_totals(database.get_all_user_ids(), update_list, all_users=True)
        database.db['ranked_lists'].update_many({'_id': {'$in': update_list}}, {'$set': {'needs_cr_total_recalc': False}})

    time.sleep(10)

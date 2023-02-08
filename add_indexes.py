import pymongo
from db import database

database.db['scores'].create_index([('user', pymongo.ASCENDING), ('cr', pymongo.ASCENDING)])
database.db['scores'].create_index([('user', pymongo.ASCENDING)])
database.db['scores'].create_index([('song_id', pymongo.ASCENDING)])
database.db['scores'].create_index([('user', pymongo.ASCENDING), ('song_id', pymongo.ASCENDING)])
database.db['users'].create_index([('date_created', pymongo.ASCENDING)])
database.db['usernames'].create_index([('terms', pymongo.TEXT)])

for pool_id in database.get_pool_ids():
    database.db['users'].create_index([('total_cr.' + pool_id, pymongo.DESCENDING)])

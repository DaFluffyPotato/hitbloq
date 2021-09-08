import pymongo
from db import database

database.db['scores'].create_index([('user', pymongo.ASCENDING), ('cr', pymongo.ASCENDING)])
database.db['scores'].create_index([('user', pymongo.ASCENDING)])
database.db['scores'].create_index([('song_id', pymongo.ASCENDING)])

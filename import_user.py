import sys

from user import User
from db import database

# just a file for manual user imports

mode = sys.argv[1]
if mode == 'add':
    username = sys.argv[2]
    scoresaber_id = sys.argv[3]
    u = User().create(database, username, scoresaber_id)
    u.refresh_scores(database)

if mode == 'update':
    user_id = sys.argv[2]
    u = database.get_users([int(user_id)])[0]
    u.refresh_scores(database)

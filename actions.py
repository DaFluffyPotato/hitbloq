import time
import json

from db import database
from user import User
import cr

BASE_64_LOGO = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAH4AAAB+CAYAAADiI6WIAAAD9klEQVR4Xu2dMW5UMRCGk4qKS9AgUXICJDrOwnG4BBISVOlyBUokGi5BlSpI7BPSiuddz+yM7X/elzLy2OP/m99vnpNN7u+Kfv349fvZsrU3r17eW8arjy27WcBfLk3Ab/rgePUzbMsfx+P4rlLG8V0yrT8Ixxd3PIB9JpRv7gAP+C4FjvYsb4mC47vKpd4gwNdj2rUjwHfJVG+QPHh1JK3mNLsXAfzkygH8ZACzlgf8LOUnrwv4yQBmLQ/4WcpPXrcs+Fkba/G0XvG25snuuqPyb+WZ3tUDPvZIsRYu4J2/oIHjnYWL453CNcJwvFNPq3A4PlholeYI8E7wUWFRTo3KJ2qeWQZI7+qjBAJ8lJKneQAfq6d5Nhx/RTIcb66piwE4PlZP82w4Hsebi+aWgKbjsy9eqh7dt8AYGQv4kWovtBbgF4IxMhXAj1R7obUAvxCMkakAfqTaC62V/h4f1b1Hve9G5bMQw7+pfPj0tJvSw8cXu98H/GoEnfkA/qAXQYAH/JkCHPWbHDzjT0LwjHc+U1cLm3bUZ9/tzxJ6tROiBbilT/pRD/gxpQn4MTrf4Xhntxx18TKI83/LAB7ws2rvbF2O+kEYcPwgoVWWyS6IKGdP+9CkCkhrnoC3KlZkPOCLgLRuA/BWxYqMB3wRkNZtHA68+tVsdv7Wgsju3lsFbf7pXLZwVudZx2fnD3grkUHjAX8SGsdvBRf1MwUcP8jB1mVwPI4/qxkcv8mR7QyrU1XGt3Sb1b2bu3rA+0oN8D7d5KMAL4/QtwHA+3STjwK8PELfBuTB+7Z9nCgVwOau/jgIfTsFvE83+SjAyyP0bQDwPt3kowAvj9C3AcD7dJOJUgdMV+8sNcA7hVMPA7w6QWf+gHcKpx4GeHWCzvwB7xROJawqYLr6KxUIeBWLBucJ+GBBVaYDvAqp4DwBHyyoynSAVyHlzPNogOnqNwUAfxLC/KFJp9GWCQM84M+KcbWPOGU7BcdvCgM+u9Qmz89RX/yoB/Blh5U96gEP+EM3cYd7j8fxOB7H79QAz/grbxmtf+YT9TdzZr3kyIN//fb98554T+8+mzStCrjsMx7wpvr+NxjHb1LgeF8BTYvC8T7pcTyO91XO7Cgc7yMg4/gWYOu2v375thui/npm1QHwm2KAt5bOoPE4PlZoHI/jYysqejYcH6sojsfxsRXlnS3K2T+/P8oUtVerW+KWEwfwt+DsjwV8v1alRgK+FM7+zQC+X6tSIwFfCmf/ZqaBp4nrh5QxEvAZqgrMCXgBSBkpAj5DVYE5AS8AKSNFwGeoKjCnDHju3mOrCfCxesrMBngZVLGJAj5WT5nZAC+DKjZRwMfqKTPbHwFhbFjfhhIwAAAAAElFTkSuQmCC'

def process_action(action):
    if action['type'] == 'add_user':
        u = User().create(database, action['user_id'])
        if u:
            u.refresh_scores(database, action['_id'])
        else:
            print('error on user add', action['user_id'])

    if action['type'] == 'update_user':
        try:
            u = database.get_users([action['user_id']])[0]
            u.refresh_scores(database, action['_id'])
        except IndexError:
            print('Invalid user for update:', action['user_id'])

    if action['type'] == 'recalculate_cr':
        cr.full_cr_update(action['map_pools'], action['_id'])

    if action['type'] == 'rank_song':
        database.rank_song(action['song_id'], action['map_pool'])

    if action['type'] == 'unrank_song':
        database.unrank_song(action['song_id'], action['map_pool'])

    if action['type'] == 'update_rank_histories':
        database.update_rank_histories(action['map_pool'], action['_id'])

    if action['type'] == 'regenerate_playlists':
        map_lists = {ranked_list['_id'] : [hash.split('|') for hash in ranked_list['leaderboard_id_list']] for ranked_list in database.get_ranked_lists()}
        for pool in map_lists:
            # there are a few unstable string hacks for the char/diff settings...
            hash_list_json = {
                'playlistTitle': pool,
                'playlistAuthor': 'Hitbloq',
                'playlistDescription': 'Hitbloq',
                'image': BASE_64_LOGO,
                'songs': [{'hash': hash[0], 'difficulties': [{'characteristic': hash[1].split('_')[2].replace('Solo', ''), 'name': hash[1].split('_')[1][0].lower() + hash[1].split('_')[1][1:]}]} for hash in map_lists[pool]],
                'syncURL': 'https://hitbloq.com/static/hashlists/' + pool + '.bplist',
            }
            f = open('static/hashlists/' + pool + '.bplist', 'w')
            json.dump(hash_list_json, f)
            f.close()

    if action['type'] == 'refresh_profiles':
        for user in database.get_all_users():
            user.refresh(database)

    database.clear_action(action['_id'])

if __name__ == "__main__":
    while True:
        next_action = database.get_next_action()

        if next_action:
            print('processing action', next_action['type'])
            process_action(next_action)
        else:
            time.sleep(3)

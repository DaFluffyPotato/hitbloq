import time
import json
import threading
import base64
import shutil
import requests
import os

from db import database
from user import User
import new_cr
from error import error_catch
from file_io import read_f

BASE_64_LOGO = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIQAAACECAYAAABRRIOnAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAJcEhZcwAADsQAAA7EAZUrDhsAAAPXSURBVHhe7d0ta5dRGMfxzWAwCE6HcwaLD2WCwWQ0iYIDX4MsmS1mg8um4VtQWNAimMRk06JYLNMxmWAwWCb4v4K/azdcO5xzn/uc7fspnqIT+XHuL/8HnF86c2lvbkR/bty3UxuOv3tmJww5Zr8C/zAICAYBkd0QrTVCaUetObghIBgEBIOASG6I3GaInsm9NclhawxuCAgGAcEgIMKGSH2mt/ZMrd0kvTcFNwQEg4BgEBD7GiJ65vb+jJz6dY7W//24ISAYBASDgAgbIveZ5/+85Y0HdjqYD2dP2KmO06vrdprG1I3BDQHBICAYBMT8wt0n0hCpz7DcRqht7CYp3SC1m4IbAoJBQDAIiOzPVLbeDKWVbpDU5hi7KbghIBgEBIOAmLwhPm5u2alNK6vLdhrW2usauY3BDQHBICAYBETy9zIOezNEpm6KiG+O1KbghoBgEBAMAqJ4Q5RuhKVHt+00zP/9Irt37tmpjNabwju3eNlOw7ghIBgEBIOACL+X4ZVuiKgRvNRmSJXbGL4paAh0jUFAMAiI7IaYuhlyv0cSSW2K2g1xdfu3nYb5n09DIAmDgGAQEM01ROlmSOV/fm5DeLlNkdoMHg2BJAwCgkFANN8QYzdD5PvjV3Y6mNINMXYzeNwQEAwCgkFAJDdE6c8L/Fi5Zqc2RQ0RNYMXPfNrN4PHDQHBICAYBMS+hvByX9uPlH4G5z5DvdyGaL0ZPG4ICAYBwSAgJm+ISGpjeKnP4Nz3LnprBo8bAoJBQDAIiOSG8Go3hVe6MeY3vthpWOrrDq03g8cNAcEgIBgERNgQXutN4UXP/NTPhEavO/TWDB43BASDgGAQEMUbwiv9vYrU9xpK21u7aKeZ3pvB44aAYBAQDAIiuSG8qZsiVWqDHPZm8LghIBgEBIOAyG4Ir/WmiBqidDNEv7+177ZyQ0AwCAgGAVG8ISJRY4zdFL4hSjdD7mcyt9ae2mmmdmNxQ0AwCAgGAVG9ISJjN8a3nc92mqn93kT0OohvjNpNwQ0BwSAgGAREcw2R6/2VC3Yaduv5pp2G1f48Q9QUCy9f2GlY6abghoBgEBAMAuLINYR3/u1rOw2r/RlI3xTR6xJeblNwQ0AwCAgGAdF9Q6wvnLTTsJuLp+x0MNc/fbVTG3xT+P+zzL/3Q0OgKAYBwSAgum8I/7rDm52fdhoWNUVvDeHlNgU3BASDgGAQEN01RPReRdQQD3d/2alPqU2RihsCgkFAMAiI5hsitRl6b4QIDYGqGAQEg4BoriFohmlxQ0AwCAgGAdF8Q9AMdXFDQDAICAaB/8zN/QUIhnNHlbUamAAAAABJRU5ErkJggg=='
LAST_UPDATES = {i: time.time() for i in range(3)}

def get_web_img_b64(url):
    if url[0] == '/':
        url = 'https://hitbloq.com' + url
    r = requests.get(url, stream=True)
    file_type = url.split('.')[-1]
    output_file = 'temp.' + file_type
    with open(output_file, 'wb') as f:
        shutil.copyfileobj(r.raw, f)
    with open(output_file, 'rb') as img_file:
        b64_data = 'data:image/png;base64,' + base64.b64encode(img_file.read()).decode('utf-8')
    os.remove(output_file)
    return b64_data if len(b64_data) > 32 else None

def playlist_song_diff(song_data):
    max_diff = 0
    for char in song_data['hitbloq']['difficulties']:
        for diff in song_data['hitbloq']['difficulties'][char]:
            diff_v = song_data['hitbloq']['difficulties'][char][diff]
            max_diff = max(diff_v, max_diff)
    return max_diff

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
            u.refresh_scores(database, action['_id'], action['queue_id'])
        except IndexError:
            print('Invalid user for update:', action['user_id'])

    if action['type'] == 'update_users':
        users = database.get_users(action['user_ids'])
        for i, user in enumerate(users):
            user.refresh_scores(database)
            if i % 10 == 0:
                database.set_action_progress(action['_id'], (i + 1) / len(action['user_ids']))
            time.sleep(0.15)

    if action['type'] == 'recalculate_cr':
        for pool in action['map_pools']:
            new_cr.CRRecalc(pool, action_id=action['_id']).run()

    if action['type'] == 'rank_song':
        database.rank_song(action['song_id'], action['map_pool'])

    if action['type'] == 'unrank_song':
        database.unrank_song(action['song_id'], action['map_pool'])

    if action['type'] == 'update_rank_histories':
        database.update_rank_histories(action['map_pool'], action['_id'])

    if action['type'] == 'regenerate_playlists':
        map_pools = {ranked_list['_id'] : ranked_list for ranked_list in database.get_ranked_lists()}
        map_lists = {ranked_list['_id'] : [(hash, hash.split('|')) for hash in ranked_list['leaderboard_id_list']] for ranked_list in database.get_ranked_lists()}

        for pool in map_lists:
            print('generating playlist for', pool)
            leaderboard_data = {leaderboard['_id']: leaderboard for leaderboard in database.get_leaderboards([hash[0] for hash in map_lists[pool]])}
            # there are a few unstable string hacks for the char/diff settings...

            playlist_img_b64 = BASE_64_LOGO
            playlist_img = map_pools[pool]['playlist_cover']
            if playlist_img:
                try:
                    img_b64 = get_web_img_b64(playlist_img)
                    if img_b64:
                        playlist_img_b64 = img_b64
                        print('used', playlist_img, 'for', pool, 'playlist')
                    elif os.path.exists('static/hashlists/' + pool + '.cover'):
                        playlist_img_b64 = read_f('static/hashlists/' + pool + '.cover')
                except:
                    pass

            authors = list(database.db['discord_users'].find({'_id': {'$in': map_pools[pool]['owners']}}))
            authors_text = ''
            for i, author in enumerate(authors):
                authors_text += author['tag'].split('#')[0]
                if i == len(authors) - 2:
                    authors_text += ', and '
                elif i < len(authors) - 2:
                    authors_text += ', '
            if authors_text == '':
                authors_text = 'unknown'

            hash_list_json = {
                'playlistTitle': map_pools[pool]['shown_name'],
                'playlistAuthor': authors_text,
                'playlistDescription': map_pools[pool]['long_description'],
                'image': playlist_img_b64,
                'songs': [],
                'syncURL': 'https://hitbloq.com/static/hashlists/' + pool + '.bplist',
            }
            song_dict = {}
            for hash in map_lists[pool]:
                characteristic = hash[1][1].split('_')[2].replace('Solo', '')
                difficulty = hash[1][1].split('_')[1][0].lower() + hash[1][1].split('_')[1][1:]
                #print(pool, leaderboard_data[hash[0]])
                song_data = {
                    'hash': hash[1][0],
                    'difficulties': [{'characteristic': characteristic, 'name': difficulty}],
                    'hitbloq': {
                        'difficulties': {
                            characteristic: {
                                difficulty: leaderboard_data[hash[0]]['star_rating'][pool] if pool in leaderboard_data[hash[0]]['star_rating'] else 0,
                            },
                        },
                    },
                }
                if hash[1][0] not in song_dict:
                    song_dict[hash[1][0]] = song_data
                else:
                    # update existing song entry instead of creating a dupe
                    if characteristic not in song_dict[hash[1][0]]['hitbloq']['difficulties']:
                        song_dict[hash[1][0]]['hitbloq']['difficulties'][characteristic] = {}
                    song_dict[hash[1][0]]['hitbloq']['difficulties'][characteristic][difficulty] = leaderboard_data[hash[0]]['star_rating'][pool]
                    song_dict[hash[1][0]]['difficulties'].append(song_data['difficulties'][0])

            for song_id in song_dict:
                hash_list_json['songs'].append(song_dict[song_id])

                hash_list_json['songs'].sort(key=playlist_song_diff, reverse=True)

            f = open('static/hashlists/' + pool + '.bplist', 'w')
            json.dump(hash_list_json, f)
            f.close()

            # copy playlist for references
            for reference in database.db['pool_references'].find({'target': pool}):
                shutil.copy('static/hashlists/' + pool + '.bplist', 'static/hashlists/' + reference['_id'] + '.bplist')

    if action['type'] == 'refresh_profiles':
        users = database.get_all_users() if not action['user_ids'] else database.get_users(action['user_ids'])
        for i, user in enumerate(users):
            user.refresh(database)
            if (i % 10 == 0):
                database.set_action_progress(action['_id'], (i + 1) / len(users))
            time.sleep(0.15)
            
    if action['type'] == 'refresh_profile':
        try:
            u = database.get_users([action['user_id']])[0]
            u.refresh(database)
        except IndexError:
            print('Invalid user for update:', action['user_id'])

    if action['type'] == 'refresh_pool_popularity':
        database.calculate_pool_popularity()

    database.clear_action(action['_id'])

def action_cleanup(action):
    database.clear_action(action['_id'])

def process_queue(queue_id=0):
    while True:
        LAST_UPDATES[queue_id] = time.time()
        next_action = database.get_next_action(queue_id)

        if next_action:
            print('processing action', next_action['type'])
            error_catch(process_action, next_action, group_id='actions_' + next_action['type'], retry=3, retry_delay=10, cleanup=action_cleanup)
        else:
            time.sleep(1.5)

if __name__ == "__main__":
    threading.Thread(target=process_queue, args=(2,)).start()
    threading.Thread(target=process_queue, args=(1,)).start()
    threading.Thread(target=process_queue, args=(0,)).start()

    if os.path.exists('temppass.txt'):
        os.remove('temppass.txt')
    
    # There's a rare hang that occurs roughly once every other month.
    # The hang seems to occur in queue #1, but the traceback on keyboard interrupt didn't reveal where the hang was.
    # It might be on one of the web or db requests. It randomly appeared without changes to Hitbloq, so it may be an interaction with BL.
    # For the time being, the main thread will watch to make sure the other threads are progressing at least one loop per hour.
    # If not, all threads are forcibly terminated and the parent task is free to restart the actions task.
    good_status = True
    while good_status:
        time.sleep(1)
        for queue_id in LAST_UPDATES:
            if time.time() - LAST_UPDATES[queue_id] > 60 * 60 * 3:
                good_status = False
    
    # forcibly kill threads
    os._exit(0)

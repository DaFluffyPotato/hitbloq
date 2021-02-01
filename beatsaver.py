import json, requests, time
from datetime import datetime

from general import char_shorten, diff_shorten

WAIT_TIME = 1

class BeatSaverInterface():
    def __init__(self):
        self.headers = {'User-Agent': 'HB_Bot/1.1b'}
        self.beatsaver_url = 'https://beatsaver.com/api/'

    def beatsaver_request(self, url):
        time.sleep(WAIT_TIME)
        for i in range(3):
            req_content = None
            try:
                time.sleep(0.3)
                req_content = requests.get(self.beatsaver_url + url, headers=self.headers).text
                return json.loads(req_content)
            except Exception as e:
                print(e)
                if req_content:
                    return req_content
                time.sleep(10)

    def lookup_song_hash(self, hash):
        map_data = self.beatsaver_request('maps/by-hash/' + hash)
        if map_data == 'Not Found':
            return None
        else:
            return map_data

    def verify_song_id(self, song_id):
        if len(song_id.split('|')) != 2:
            return False

        difficulty_settings = song_id.split('|')[-1]

        if len(difficulty_settings.split('_')) != 3:
            return False

        junk, difficulty, characteristic = difficulty_settings.split('_')

        if junk != '':
            return False

        hash = song_id.split('|')[0]

        if characteristic not in char_shorten:
            return False

        if difficulty not in diff_shorten:
            return False

        if characteristic[:4] == 'Solo':
            characteristic = characteristic[4:]

        difficulty = difficulty[0].lower() + difficulty[1:]

        song_data = self.lookup_song_hash(hash)

        if not song_data:
            return False

        for c in song_data['metadata']['characteristics']:
            if c['name'] == characteristic:
                if difficulty in c['difficulties']:
                    if c['difficulties'][difficulty] != None:
                        return song_data

        return False

import json, requests, time
from datetime import datetime

from general import char_shorten, diff_shorten

WAIT_TIME = 1

class BeatSaverInterface():
    def __init__(self):
        self.headers = {'User-Agent': 'HB_Bot/1.2b'}
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
        hash = hash.upper()
        map_data = self.beatsaver_request('maps/hash/' + hash)
        if 'error' in map_data:
            return None
        else:
            for i, ver in sorted(enumerate(map_data['versions']), reverse=True):
                if ver['hash'].upper() != hash:
                    map_data['versions'].pop(i)
            return map_data

    def get_diff_data(self, map_data, difficulty, characteristic):
        if len(map_data['versions']):
            for diff in map_data['versions'][0]['diffs']:
                if diff['characteristic'] == characteristic:
                    if diff['difficulty'] == difficulty:
                        return diff

    def verify_song_id(self, song_id):
        if len(song_id.split('|')) != 2:
            return False

        difficulty_settings = song_id.split('|')[-1]

        if len(difficulty_settings.split('_')) != 3:
            print('invalid hash: bad difficulty args')
            return False

        junk, difficulty, characteristic = difficulty_settings.split('_')

        if junk != '':
            print('invalid hash: bad difficulty args')
            return False

        hash = song_id.split('|')[0].upper()

        if characteristic not in char_shorten:
            print('invalid hash: char not enabled')
            return False

        if difficulty not in diff_shorten:
            print('invalid hash: diff not enabled')
            return False

        if characteristic[:4] == 'Solo':
            characteristic = characteristic[4:]

        song_data = self.lookup_song_hash(hash)

        if not song_data:
            print('invalid hash: beatsaver hash not found')
            return False

        if len(song_data['versions']):
            for diff in song_data['versions'][0]['diffs']:
                if diff['characteristic'] == characteristic:
                    if diff['difficulty'] == difficulty:
                        return song_data

        print('invalid hash: no matching beatsaver diff/char:', characteristic, difficulty)
        return False

import json, requests, time
from datetime import datetime

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

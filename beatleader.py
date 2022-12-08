import json, requests, time
from datetime import datetime

from config_loader import config

class BeatLeaderInterface:
    def __init__(self, database=None, queue_id=0):
        self.headers = {'User-Agent': 'Hitbloq/1.3b'}
        self.database = database
        self.queue_id = queue_id
        self.all_endpoints = config['beatleader_endpoints']["0"]
        self.beatleader_url = self.all_endpoints[0]
        print('created BeatLeader interface with endpoint set:', self.all_endpoints)

    def bl_req(self, url):
        for i in range(5):
            try:
                req = requests.get(self.beatleader_url + url, headers=self.headers)
                req_content = req.text
                return json.loads(req_content)
            except Exception as e:
                print(e)
                time.sleep(15)

    def convert_score_format(self, scores):
        modified_scores = []
        for score in scores:
            new_score = {
                'score': {
                    'modifiedScore': score['modifiedScore'],
                    'maxCombo': score['maxCombo'],
                    'missedNotes': score['missedNotes'],
                    'badCuts': score['badCuts'],
                    'hmd': score['hmd'],
                    'epochTime': score['timepost'],
                    'modifiers': score['modifiers'],
                },
                'leaderboard': {
                    'songHash': score['leaderboard']['song']['hash'].upper(),
                    'difficulty': {
                        'difficultyRaw': '_' + score['leaderboard']['difficulty']['difficultyName'] + '_Solo' + score['leaderboard']['difficulty']['modeName']
                    }
                }
            }
            modified_scores.append(new_score)
        return modified_scores

    def fetch_until(self, bl_id, epoch, limit=100):
        scores = []
        c = 0
        looking = True
        while looking:
            req_url = 'player/' + bl_id + '/scores?page=' + str(c + 1) + '&sortBy=date&order=desc&count=' + str(limit)
            print('checking', req_url)
            try:
                new_dat = self.bl_req(req_url)
                if new_dat == None:
                    print('skipping due to failures')
                    continue
            except KeyError:
                print('invalid response')
                break

            if not len(new_dat['data']):
                print('no scores')
                break

            if len(new_dat['data']):
                for score in new_dat['data']:
                    if score['timepost'] < (epoch - 300):
                        looking = False
                    else:
                        scores.append(score)
            c += 1

        print('Finish BL lookup for', bl_id)
        return self.convert_score_format(scores)
import json, requests, time
from datetime import datetime

from config_loader import config

def convert_epoch(t):
    utc_time = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
    epoch = (utc_time - datetime(1970, 1, 1)).total_seconds()
    return epoch

class ScoresaberInterface():
    def __init__(self, database, queue_id=0):
        self.headers = {'User-Agent': 'Hitbloq/1.4b'}
        self.database = database
        self.queue_id = queue_id
        self.all_endpoints = config['scoresaber_endpoints'][str(queue_id)]
        self.scoresaber_url = self.all_endpoints[0]
        print('created ScoreSaber interface with endpoint set:', self.all_endpoints)

    def ss_req(self, url):
        for i in range(5):
            try:
                req = requests.get(self.scoresaber_url + url, headers=self.headers)
                req_content = req.text
                try:
                    print(req.headers['X-RateLimit-Limit'], req.headers['X-RateLimit-Remaining'], req.headers['X-RateLimit-Reset'])
                except:
                    print('no headers found. received SS response.')
                req_json = json.loads(req_content)
                if 'statusCode' in req_json:
                    print('ratelimited.', req_json)
                    raise ValueError
                return req_json
            except Exception as e:
                print(e)
                time.sleep(15)

    def convert_score_format(self, scores):
        modified_scores = []
        for score in scores:
            hmd = 'unknown'
            if not score:
                raise AttributeError(score)
            if ('device' in score['score']) and ('hmd' in score['score']['device']):
                hmd = score['score']['device']['hmd']
            new_score = {
                'score': {
                    'modifiedScore': score['score']['modifiedScore'],
                    'maxCombo': score['score']['maxCombo'],
                    'missedNotes': score['score']['missedNotes'],
                    'badCuts': score['score']['badCuts'],
                    'hmd': hmd,
                    'epochTime': score['score']['createdAt'],
                    'modifiers': ','.join(score['score']['mods']),
                },
                'leaderboard': {
                    'songHash': score['leaderboard']['map']['hash'].upper(),
                    'difficulty': {
                        'difficultyRaw': score['leaderboard']['difficulty']['rawDifficulty'],
                    }
                },
                'src': 'ss',
            }
            modified_scores.append(new_score)
        return modified_scores

    def fetch_until(self, ss_id, epoch, limit=100):
        looking = True
        total_dat = []
        c = 0
        while looking:
            req_url = 'v2/players/' + ss_id + '/scores?sort=recent&withMetadata=false&page=' + str(c + 1) + '&limit=' + str(limit)
            print('checking', req_url)
            try:
                new_dat = self.ss_req(req_url)
                if new_dat == None:
                    print('skipping due to failures')
                    continue
            except KeyError:
                if ('error' not in new_dat) or (new_dat['error'] != 'This user has not set any scores!'):
                    print(new_dat)
                new_dat = []

            # new api case for end of pages
            if ('data' in new_dat) and (not len(new_dat['data'])):
                new_dat = []
                print('reached end of profile')

            save_dat = []
            if new_dat == []:
                looking = False
            else:
                if 'data' not in new_dat:
                    print('ERROR')
                    print(new_dat)

                    # hack because umbra never fixed thousands of broken scores on SS.
                    c += 1
                    continue

                # umbranox did a lil' trolling and changed the API again
                if not len(new_dat['data']):
                    looking = False
                    print('reached end of profile')

                else:
                    for score in new_dat['data']:
                        if convert_epoch(score['score']['createdAt']) < (epoch - 300): # -300 to be safe
                            looking = False
                        else:
                            score['score']['createdAt'] = convert_epoch(score['score']['createdAt'])
                            score['leaderboard']['map']['hash'] = score['leaderboard']['map']['hash'].upper()
                            save_dat.append(score)
                    total_dat += save_dat
            c += 1
        print('Finished SS lookup for', ss_id)
        return self.convert_score_format(total_dat)

    def fetch_all_scores(self, ss_id):
        return self.fetch_until(ss_id, 0, limit=100)

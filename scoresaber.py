import json, requests, time
from datetime import datetime

from config_loader import config

def convert_epoch(t):
    utc_time = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
    epoch = (utc_time - datetime(1970, 1, 1)).total_seconds()
    return epoch

class ScoresaberInterface():
    def __init__(self, database, queue_id=0):
        self.headers = {'User-Agent': 'Hitbloq/1.2b'}
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
                return json.loads(req_content)
            except Exception as e:
                print(e)
                time.sleep(15)

    def fetch_until(self, ss_id, epoch, limit=100):
        looking = True
        total_dat = []
        c = 0
        while looking:
            req_url = 'player/' + ss_id + '/scores/?sort=recent&withMetadata=false&page=' + str(c + 1) + '&limit=' + str(limit)
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
            if ('errorMessage' in new_dat) and (new_dat['errorMessage'] == 'Scores not found'):
                new_dat = []
                print('reached end of profile')

            save_dat = []
            if new_dat == []:
                looking = False
            else:
                for score in new_dat['playerScores']:
                    if convert_epoch(score['score']['timeSet']) < (epoch - 300): # -300 to be safe
                        looking = False
                    else:
                        score['score']['epochTime'] = convert_epoch(score['score']['timeSet'])
                        score['leaderboard']['songHash'] = score['leaderboard']['songHash'].upper()
                        save_dat.append(score)
                total_dat += save_dat
            c += 1
        print('Finished SS lookup for', ss_id)
        return total_dat

    def fetch_all_scores(self, ss_id):
        return self.fetch_until(ss_id, 0, limit=100)

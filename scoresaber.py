import json, requests, time
from datetime import datetime

def convert_epoch(t):
    utc_time = datetime.strptime(t, '%Y-%m-%dT%H:%M:%S.%fZ')
    epoch = (utc_time - datetime(1970, 1, 1)).total_seconds()
    return epoch

class ScoresaberInterface():
    def __init__(self, database):
        self.headers = {'User-Agent': 'Hitbloq/1.1b'}
        self.database = database
        self.scoresaber_url = 'https://new.scoresaber.com/api/'

    def ss_req(self, url):
        for i in range(3):
            try:
                print('request start!')
                req = requests.get(self.scoresaber_url + url, headers=self.headers)
                print('req received!')
                req_content = req.text
                print(req.headers['X-RateLimit-Limit'], req.headers['X-RateLimit-Remaining'], req.headers['X-RateLimit-Reset'])
                return json.loads(req_content)
            except Exception as e:
                print(e)
                time.sleep(20)

    def fetch_until(self, ss_id, epoch):
        looking = True
        total_dat = []
        c = 0
        while looking:
            req_url = 'player/' + ss_id + '/scores/recent/' + str(c)
            print('checking', req_url)
            try:
                time.sleep(0.37)
                new_dat = self.ss_req(req_url)
                if new_dat == None:
                    print('skipping due to failures')
                    continue
                new_dat = new_dat['scores']
            except KeyError:
                if ('error' not in new_dat) or (new_dat['error'] != 'This user has not set any scores!'):
                    print(new_dat)
                new_dat = []
            save_dat = []
            if new_dat == []:
                looking = False
            else:
                for score in new_dat:
                    if convert_epoch(score['timeSet']) < (epoch - 300): # -300 to be safe
                        looking = False
                    else:
                        score['epochTime'] = convert_epoch(score['timeSet'])
                        save_dat.append(score)
                total_dat += save_dat
            c += 1
        print('Finished SS lookup for', ss_id)
        return total_dat

    def fetch_all_scores(self, ss_id):
        return self.fetch_until(ss_id, 0)

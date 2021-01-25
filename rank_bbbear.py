# lololololol

from db import database
import beatsaver
import general

bs = beatsaver.BeatSaverInterface()

results = []
for i in range(5):
    print(i)
    results.append(bs.beatsaver_request('maps/uploader/5cff0b7398cc5a672c84f3ca/' + str(i)))

leaderboard_ids = []

for page in results:
    for doc in page['docs']:
        doc['hash'] = doc['hash'].upper()
        for characteristic in doc['metadata']['characteristics']:
            if characteristic['name'] == 'Standard':
                for difficulty in characteristic['difficulties']:
                    if characteristic['difficulties'][difficulty] != None:
                        leaderboard_ids.append(doc['hash'] + '|_' + difficulty[0].upper() + difficulty[1:] + '_SoloStandard')

for i, leaderboard_id in enumerate(leaderboard_ids):
    print(i, len(leaderboard_ids))
    database.rank_song(leaderboard_id, 'bbbear')

var poolID;

function genLeaderboard(status, data) {
  for (const score of data) {
    var newHTML = useTemplate('new_leaderboard_entry',
        {
            'username': '<a class="link" href="/user/' + score['user'] + '?pool=' + poolID + '">' + score['username'] + '</a>',
            'pfp': score['profile_pic'],
            'rank': '#' + score['rank'],
            'cr': Math.round(score['cr'][poolID] * 100) / 100 + 'cr',
            'accuracy': score['accuracy'] + '%',
            'score': '<span class="leaderboard-score">(' + numWithCommas(score['score']) + ')</span>',
            'date': score['date_set'],
        }
    );

    if (score['banner_image'] != null) {
      newHTML.style.background = 'linear-gradient(to right, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.15) 40%, rgba(0, 0, 0, 0.35) 80%, rgba(0, 0, 0, 1) 100%), url("' + score['banner_image'] + '") no-repeat';
      newHTML.style.backgroundSize = "1200px 100%";
    }

    document.getElementById('leaderboard-entries-container').appendChild(newHTML);
  }
}

function finishedTemplateLoading() {
  var path = window.location.pathname.split('/');
  leaderboardID = path[path.length - 1];

  var page = new URL(location.href).searchParams.get('page');
  poolID = new URL(location.href).searchParams.get('pool');

  if (page == null) {
    page = 0;
  }
  if (poolID == null) {
    poolID = 'bbbear';
  }

  getJSON(window.location.origin + '/api/leaderboard/' + leaderboardID + '/scores_extended/' + page + '?per_page=20', genLeaderboard);
}

window.addEventListener('load', () => {
    loadTemplates(['new_leaderboard_entry'], finishedTemplateLoading);
})

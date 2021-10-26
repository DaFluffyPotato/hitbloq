var userID = window.location.pathname.split('/');
userID = userID[userID.length - 1];

function genScores(status, data) {
  for (const score of data) {
    var newHTML = useTemplate('new_player_profile_score',
      {
          'cover': score['song_cover'],
          'rank': score['song_rank'],
          'name': score['song_name'],
          'difficulty': score['difficulty'],
          'date': score['date_set'],
          'raw_cr': score['cr_received'],
          'weighted_cr': score['weighted_cr'],
          'accuracy': score['accuracy'],
      }
    );

    document.getElementById('player-profile-scores').appendChild(newHTML);
  }
}

function finishedTemplateLoading() {
  getJSON(window.location.origin + '/api/user/' + userID + '/scores' + window.location.search, genScores);
}

window.addEventListener('load', () => {
    //console.log(document.getElementsByClassName('map-pool-card')[0].innerHTML);

    loadTemplates(['new_player_profile_score'], finishedTemplateLoading);
})

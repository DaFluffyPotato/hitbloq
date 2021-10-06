function genPlayerLeaderboard(status, json_data) {
  for (const player of json_data['ladder']) {
    var change_str = player['rank_change'].toString();
    if (change_str[0] != '-') {
      if (change_str != '0') {
        change_str = '<span style="color: #42B129">+' + change_str + '</span>';
      }
    } else {
      change_str = '<span style="color: rgb(255, 0, 68)">' + change_str + '</span>';
    }

    var newHTML = useTemplate('new_player_leaderboard_entry',
        {
            'username': '<a class="link" href="/user/' + player['user'] + '">' + player['username'] + '</a>',
            'pfp': player['profile_pic'],
            'rank': '#' + player['rank'],
            'cr': Math.round(player['cr'] * 100) / 100 + 'cr',
            'change': change_str,
        }
    );

    if (player['banner_image'] != null) {
      newHTML.style.background = 'linear-gradient(to right, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.15) 40%, rgba(0, 0, 0, 0.35) 80%, rgba(0, 0, 0, 1) 100%), url("' + player['banner_image'] + '") no-repeat';
      newHTML.style.backgroundSize = "1200px 100%";
    }

    document.getElementById('player-leaderboard-entries-container').appendChild(newHTML);
  }
}

function finishedTemplateLoading() {
  var path = window.location.pathname.split('/');
  var pool_id = path[path.length - 1];
  var page = new URL(location.href).searchParams.get('page');
  if (page == null) {
    page = 0;
  }
  getJSON(window.location.origin + '/api/ladder/' + pool_id + '/players/' + page + '?per_page=50', genPlayerLeaderboard);
}

window.addEventListener('load', () => {
    //console.log(document.getElementsByClassName('map-pool-card')[0].innerHTML);

    loadTemplates(['new_player_leaderboard_entry'], finishedTemplateLoading);
})

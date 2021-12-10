var poolID = window.location.pathname.split('/');
poolID = poolID[poolID.length - 1];

function genMapPool(status, data) {
  var pool = data;
  var newHTML = useTemplate('new_map_pool_card_alt',
      {
          'title': pool['banner_title_hide'] ? '' : pool['shown_name'],
          'description': pool['short_description'] ? pool['short_description'] : 'The ' + pool['shown_name'] + ' map pool.',
          'cover': pool['cover'],
          'player_count': numWithCommas(pool['player_count']),
          'pool_id': pool['_id'],
          'download_url': '/static/hashlists/' + pool['_id'] + '.bplist',
          'popularity': numWithCommas(pool['priority']),
      }
  );
  document.getElementById('pool-card').appendChild(newHTML);
}

function genPlayerLeaderboard(status, data) {
  console.log(data);

  for (const player of data['ladder']) {
    if (player['rank_change'] != undefined) {
      var changeStr = player['rank_change'].toString();
      if (changeStr[0] != '-') {
        if (changeStr != '0') {
          changeStr = '<span style="color: #42B129">+' + changeStr + '</span>';
        }
      } else {
        changeStr = '<span style="color: rgb(255, 0, 68)">' + changeStr + '</span>';
      }
    }

    var newHTML = useTemplate('new_player_leaderboard_entry_alt',
        {
            'username': '<a class="link" href="/user/' + player['user'] + '?pool=' + poolID + '">' + player['username'] + '</a>',
            'pfp': player['profile_pic'],
            'rank': (player['rank'] != null) ? '#' + player['rank'] : '',
            'cr': Math.round(player['cr'] * 100) / 100 + 'cr',
        }
    );

    if (player['banner_image'] != null) {
      newHTML.style.background = 'linear-gradient(to right, rgba(0, 0, 0, 1) 0%, rgba(0, 0, 0, 0.15) 40%, rgba(0, 0, 0, 0.35) 80%, rgba(0, 0, 0, 1) 100%), url("' + player['banner_image'] + '") no-repeat';
      newHTML.style.backgroundSize = "1200px 100%";
    }

    document.getElementById('leaderboard-contents').appendChild(newHTML);
  }
}

function finishedTemplateLoading() {
  getJSON(window.location.origin + '/api/ranked_list/' + poolID, genMapPool);
  getJSON(window.location.origin + '/api/ladder/' + poolID + '/players/0?per_page=20', genPlayerLeaderboard);
}

window.addEventListener('load', () => {
    loadTemplates(['new_map_pool_card_alt', 'new_player_leaderboard_entry_alt'], finishedTemplateLoading);
})

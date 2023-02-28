var poolID = window.location.pathname.split('/');
var lazyLoading = false;
var lazyLoadIndex = 0;
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
        changeStr = '<span style="color: rgb(0, 153, 219)">' + changeStr + '</span>';
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

function genPoolFeed(status, data) {
  for (const post of data) {
    var newHTML = useTemplate('new_pool_ranking_post',
        {
            'action': (post['status'] == 'ranked') ? 'Ranked' : 'Unranked',
            'cover': post['leaderboard_data'][0]['cover'],
            'name': post['leaderboard_data'][0]['name'],
            'difficulty': post['leaderboard_data'][0]['difficulty'],
            'stars': (poolID in post['leaderboard_data'][0]['star_rating']) ? post['leaderboard_data'][0]['star_rating'][poolID] + '★' : '',
            'date': post['date'],
            'leaderboard_id': post['short_leaderboard_id'],
            'pool_id': poolID,
        }
    );
    document.getElementById('pool-feed').appendChild(newHTML);
  }
  lazyLoadIndex++;
  lazyLoading = false;
}

function finishedTemplateLoading() {
  getJSON(window.location.origin + '/api/ranked_list/' + poolID, genMapPool);
  getJSON(window.location.origin + '/api/ladder/' + poolID + '/players/0?per_page=20', genPlayerLeaderboard);
  getJSON(window.location.origin + '/api/pool_feed/' + poolID, genPoolFeed);
}

window.addEventListener('load', () => {
  loadTemplates(['new_map_pool_card_alt', 'new_player_leaderboard_entry_alt', 'new_pool_ranking_post'], finishedTemplateLoading);
  content = document.getElementById('content');
  content.onscroll = function(ev) {
    if (content.scrollTop === (content.scrollHeight - content.offsetHeight)) {
        if (!lazyLoading) {
          lazyLoading = true;
          getJSON(window.location.origin + '/api/pool_feed/' + poolID + '?page=' + lazyLoadIndex, genPoolFeed);
        }
    }
  };
})

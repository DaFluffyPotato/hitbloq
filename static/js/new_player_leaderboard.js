var poolID;

function genPlayerLeaderboard(status, jsonData) {
  for (const player of jsonData['ladder']) {
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

    var newHTML = useTemplate('new_player_leaderboard_entry',
        {
            'username': '<a class="link" href="/new/user/' + player['user'] + '?pool=' + poolID + '">' + player['username'] + '</a>',
            'pfp': player['profile_pic'],
            'rank': (player['rank'] != null) ? '#' + player['rank'] : '',
            'cr': Math.round(player['cr'] * 100) / 100 + 'cr',
            'change': (player['rank_change'] != null) ? changeStr : '',
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
  poolID = path[path.length - 1];
  var page = new URL(location.href).searchParams.get('page');
  var search = new URL(location.href).searchParams.get('search');
  if (page == null) {
    page = 0;
  }
  if (search != null) {
    var navButtons = document.getElementsByClassName('nav-button-l');
    for (var i = 0; i < navButtons.length; i++) {
      navButtons[i].style.display = 'none';
    }
    var navButtons = document.getElementsByClassName('nav-button-r');
    for (var i = 0; i < navButtons.length; i++) {
      navButtons[i].style.display = 'none';
    }

    getJSON(window.location.origin + '/api/ladder/' + poolID + '/players/' + page + '?per_page=50&search=' + search, genPlayerLeaderboard);
  } else {
    getJSON(window.location.origin + '/api/ladder/' + poolID + '/players/' + page + '?per_page=50', genPlayerLeaderboard);
  }
}

window.addEventListener('load', () => {
    loadTemplates(['new_player_leaderboard_entry'], finishedTemplateLoading);

    document.getElementById('player-search').onkeypress = (e) => {
    if (!e) {
      e = window.event;
    }

    var keyCode = e.code || e.key;

    if (keyCode == 'Enter') {
     window.location = window.location.pathname + '?search=' + document.getElementById('player-search').value;
    }
  }
})

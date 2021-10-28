var poolID;

function genRankedList(status, data) {
  console.log(data);
  for (const song of data) {
    var newHTML = useTemplate('new_ranked_list_entry',
        {
            'name': '<a class="link" href="/leaderboard/' + song['song_id'] + '?pool=' + poolID + '">' + song['song_name'] + '</a>',
            'cover': song['song_cover'],
            'difficulty': song['song_difficulty'],
            'play_count': song['song_plays'],
            'stars': song['song_stars'] + '★',
        }
    );

    document.getElementById('ranked-list-entries-container').appendChild(newHTML);
  }
}

function finishedTemplateLoading() {
  var path = window.location.pathname.split('/');
  poolID = path[path.length - 1];
  var page = new URL(location.href).searchParams.get('page');
  if (page == null) {
    page = 0;
  }
  getJSON(window.location.origin + '/api/ranked_list_detailed/' + poolID + '/' + page, genRankedList);
}

window.addEventListener('load', () => {
    loadTemplates(['new_ranked_list_entry'], finishedTemplateLoading);
})

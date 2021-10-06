var poolData;

function genMapPools(status, data) {
  poolData = data;
  window.setInterval(genMapPool, 50);
}

function genMapPool() {
  if (poolData.length > 0) {
    const pool = poolData[0];
    var newHTML = useTemplate('new_map_pool_card',
        {
            'title': pool['banner_title_hide'] ? '' : pool['title'],
            'description': pool['short_description'],
            'cover': pool['banner_image'],
            'player_count': numWithCommas(pool['player_count']),
            'pool_id': pool['id'],
            'download_url': pool['download_url'],
            'popularity': numWithCommas(pool['popularity']),
        }
    );
    document.getElementById('map-pools-container').appendChild(newHTML);
    poolData.splice(0, 1);
  }
}

function finishedTemplateLoading() {
  getJSON(window.location.origin + '/api/map_pools_detailed', genMapPools);
}

window.addEventListener('load', () => {
    //console.log(document.getElementsByClassName('map-pool-card')[0].innerHTML);

    loadTemplates(['new_map_pool_card'], finishedTemplateLoading);
})

var userID = window.location.pathname.split('/');
userID = userID[userID.length - 1];

var rankData;
var canvas;
var canvasHover = false;
var rankCircle;
var rankDataDiv;

window.onload = () => {
  canvas = document.getElementById('rank-history');
  rankCircle = document.getElementById('rank-circle');
  rankDataDiv = document.getElementById('rank-data');
}

window.onresize = () => {
  updateRankHistory(200, ranData);
}

window.onmousemove = () => {
  if (canvas) {
    mx = event.clientX - canvas.getBoundingClientRect().x;
    my = event.clientY - canvas.getBoundingClientRect().y;
    if ((mx >= 0 && mx <= canvas.width) && (my >= 0 && my <= canvas.height)) {
      updateRankHistory(200, rankData, {'x': mx, 'y': my});
      canvasHover = true;
    } else if (canvasHover) {
      canvasHover = false;
      updateRankHistory(200, rankData);
    }
  }
}

function updateRankHistory(status, data, mouse) {
  rankData = data;

  canvas.height = canvas.clientHeight;
  canvas.width = canvas.clientWidth;
  var ctx = canvas.getContext('2d');
  var baseline = canvas.height / 2;
  var dayWidth = canvas.width / (rankData.history.length - 1);
  ctx.strokeStyle = 'rgb(255, 0, 68)';

  var maxRank = Math.max(...rankData.history);
  var minRank = Math.min(...rankData.history);
  if (minRank == maxRank) {
    minRank -= 0.5;
    maxRank += 0.5;
  }

  var lastHeight = (rankData.history[0] - minRank) / (maxRank - minRank);

  ctx.fillStyle = 'rgb(0, 0, 0)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  for (let i = 0; i < rankData.history.length - 1; i++) {
    ctx.moveTo(i * dayWidth, lastHeight * canvas.height * 0.7 + canvas.height * 0.15);
    lastHeight = (rankData.history[i + 1] - minRank) / (maxRank - minRank);
    ctx.lineTo((i + 1) * dayWidth, lastHeight * canvas.height * 0.7 + canvas.height * 0.15);
    ctx.stroke();
  }

  if (mouse) {
    dayIndex = Math.floor(mouse.x / dayWidth + 0.5);
    daysAgo = rankData.history.length - dayIndex - 1;
    daysAgoText = (daysAgo != 0) ? daysAgo + ' days ago' : 'today';

    ctx.moveTo(dayIndex * dayWidth, 0);
    ctx.lineTo(dayIndex * dayWidth, canvas.height);
    ctx.stroke();
    var basePos = {'x': dayIndex * dayWidth, 'y': ((rankData.history[dayIndex] - minRank) / (maxRank - minRank)) * canvas.height * 0.7 + canvas.height * 0.15};
    rankCircle.style.left = basePos.x;
    rankCircle.style.top = basePos.y;
    rankCircle.style.display = 'block';

    rankDataDiv.style.left = basePos.x + 14;
    rankDataDiv.style.top = basePos.y + 4;
    rankDataDiv.innerHTML = 'Rank: #' + rankData.history[dayIndex] + '<br>' + daysAgoText;
    rankDataDiv.style.display = 'block';
  } else {
    rankCircle.style.display = 'none';
    rankDataDiv.style.display = 'none';
  }
}

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
  let params = new URLSearchParams(location.search)
  var sortMode = (params.get('sort')) ? params.get('sort') : 'cr';
  var mapPool = (params.get('pool')) ? params.get('pool') : 'bbbear';

  getJSON(window.location.origin + '/api/player_rank/' + mapPool + '/' + userID, updateRankHistory);

  document.getElementById(sortMode + '-sort-link').style.boxShadow = '0px -2px 0px rgb(255, 0, 68) inset';

  loadTemplates(['new_player_profile_score'], finishedTemplateLoading);
})

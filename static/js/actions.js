function getJSON(url, callback) {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'json';
    xhr.onload = function() {
      var status = xhr.status;
      if (status === 200) {
        callback(null, xhr.response);
      } else {
        callback(status, xhr.response);
      }
    };
    xhr.send();
};

function epoch() {
  current_date = new Date();
  return Math.round(current_date.getTime() / 1000);
}

function refreshActions() {
  getJSON('/api/actions', updateActions);
}

function updateActions(status, action_data) {
  var new_html = '';
  action_data.forEach((action, i) => {
    if (i == 0) {
      new_html += '<div class="action-entry" style="box-shadow: -1px 0px 0px 0px rgb(86, 221, 145), 0px 0px 6px 0px rgba(0, 0, 0, 0.28) inset;"><div class="action-progress-container"><div class="action-progress" style="width: ' + (action['progress'] * 100) + '%"></div></div>' + action['type'] + ' <i>(created ' + Math.round(epoch() - action['time']) + 's ago)</i><br><br>';
    } else {
      new_html += '<div class="action-entry">' + action['type'] + ' <i>(created ' + Math.round(epoch() - action['time']) + 's ago)</i><br>';
    }
    Object.keys(action).forEach((key) => {
      if (!['progress', 'type', 'time'].includes(key)) {
        new_html += key + ': ' + action[key] + '<br>';
      }
    });
    new_html += '</div>';
  });
  document.getElementById('action_list').innerHTML = new_html;
}

refreshActions();
setInterval(refreshActions, 1000);

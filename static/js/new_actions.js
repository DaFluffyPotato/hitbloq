function epoch() {
  currentDate = new Date();
  return Math.round(currentDate.getTime() / 1000);
}

function refreshActions() {
  getJSON('/api/actions', updateActions);
}

function refreshQueueStatus() {
  getJSON('/api/queue_statuses', updateQueueStatus);
}

function updateActions(status, action_data) {
  var newHTML = '';
  action_data.forEach((action, i) => {
    var timePassed = Math.round(epoch() - action['time'])
    var hoursPassed = Math.floor(timePassed / (60 * 60))
    var timePassedStr = Math.floor((timePassed % (60 * 60)) / 60) + 'm ' + (timePassed % 60) + 's';
    if (hoursPassed > 0.5) {
      timePassedStr = hoursPassed + 'h ' + timePassedStr;
    }

    if (action['progress'] != 0) {
      newHTML += '<div class="action-entry" style="box-shadow: -1px 0px 0px 0px rgb(0, 153, 219), 0px 0px 6px 0px rgba(0, 0, 0, 0.28) inset;">' + action['type'] + ' <i>(created ' + timePassedStr + ' ago)</i><br><div class="action-progress-container"><div class="action-progress" style="width: ' + (action['progress'] * 100) + '%"></div></div>';
    } else {
      newHTML += '<div class="action-entry">' + action['type'] + ' <i>(created ' + timePassedStr + ' ago)</i><br>';
    }
    Object.keys(action).forEach((key) => {
      if (!['progress', 'type', 'time'].includes(key)) {
        newHTML += key + ': ' + action[key] + '<br>';
      }
    });
    newHTML += '</div>';
  });
  document.getElementById('actions-container').innerHTML = newHTML;
}

function updateQueueStatus(status, queue_statuses) {
  var newHTML = '';
  for (let i = 0; i < 3; i++) {
    newHTML += '<h3>Queue ' + i + ' - ' + (queue_statuses[i.toString()] ? 'busy' : 'idle') + '</h3>';
  }
  document.getElementById('actions-status-container').innerHTML = newHTML;
}

refreshActions();
refreshQueueStatus();
setInterval(refreshActions, 2000);
setInterval(refreshQueueStatus, 5000);

function postAddUser(status, json_response) {
  if (json_response['status'] == 'success') {
    document.getElementById('user-addition-notification').innerHTML = '<p>Added to the <a href="/actions" class="highlight link">Action Queue</a>! After the Score Saber data has been downloaded, you can search for your Score Saber username.</p>';
  } else {
    document.getElementById('user-addition-notification').innerHTML = '<p>It appears you\'ve hit the user addition limit. Please add from the <a href="https://discord.gg/pxWwtWJ" class="highlight link">Discord server</a> where we can get a name associated with the request.</p>';
  }
}

function add_user() {
  var value = document.getElementById('user-addition-input').value;
  if (value != '') {
    sendJSON('/api/add_user', {'url': value}, postAddUser);
  }
}

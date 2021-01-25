function submitSearch(form) {
    var value = form.input.value.replace(/[^ a-zA-Z0-9_-]/, "")
	if (value != '') {
		window.location.href = "/search/" + value;
	}
    return false;
}

function set_map_pool_cookie(map_pool) {
  document.cookie = "map_pool=" + map_pool + ";";
  window.location.reload(true);
}

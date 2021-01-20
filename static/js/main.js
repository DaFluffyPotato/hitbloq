function set_map_pool_cookie(map_pool) {
  document.cookie = "map_pool=" + map_pool + ";";
  window.location.reload(true);
}

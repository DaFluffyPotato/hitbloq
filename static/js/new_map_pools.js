function genMapPools(status, data) {
  console.log(data);
}

window.addEventListener("load", () => {
    //console.log(document.getElementsByClassName('map-pool-card')[0].innerHTML);

    map_pool_template = getJSON(window.location.origin + '/api/get_template/new_map_pool_card', loadTemplate)

    getJSON(window.location.origin + '/api/map_pools_detailed', genMapPools);
})

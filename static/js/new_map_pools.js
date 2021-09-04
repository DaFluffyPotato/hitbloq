function genMapPools(status, data) {
  console.log(data);
}

getJSON('https://hitbloq.com/api/map_pools_detailed', genMapPools);

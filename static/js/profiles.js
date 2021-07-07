// var rankHistory = [1, 5, 6, 7, 29, 11, 13, 14, 6, 7, 2, 8, 1, 14, 30, 60, 20, 10, 30, 10, 11, 13, 14, 6, 7, 2, 8, 1, 14, 30, 60]
var canvas = document.getElementsByClassName("rank-canvas")[0]
var canvasWrapper = document.getElementsByClassName("rank-graph")[0]
var rankLine = document.getElementsByClassName("rank-line")[0]
var rankCircle = document.getElementsByClassName("rank-circle")[0]
var rankInfo = document.getElementsByClassName("rank-graph-info")[0]
var rankInfoGlobal = document.getElementsByClassName("rank-info-global")[0]
var rankInfoTime = document.getElementsByClassName("rank-info-time")[0]
var ctx = canvas.getContext("2d")

canvas.height = canvasWrapper.clientHeight
canvas.width = canvasWrapper.clientWidth

// How many pixels between two subsequent points
var heightUnit
var widthUnit
var lowestRank
var highestRank

var mouseCanvasX
var mouseCanvasY

var lastUserUpdate

window.onmousemove = () => {
    mouseCanvasX = event.clientX - canvasWrapper.getBoundingClientRect().x
    mouseCanvasY = event.clientY - canvasWrapper.getBoundingClientRect().y

    if((mouseCanvasX >= 0 && mouseCanvasX <= canvas.width) && (mouseCanvasY >= 0 && mouseCanvasY <= canvas.height)) {
        showRankInfo()
    } else {
        rankLine.style.display = "none";
        rankCircle.style.display = "none";
        rankInfo.style.display = "none";
    }
}

window.addEventListener("load", () => {
    updateRankGraphData(rankHistory)
    heightUnit = canvas.height / lowestRank
    widthUnit = canvas.width / (rankHistory.length - 1)
    renderGraph(rankHistory)
    lastUserUpdate = document.getElementById("last-manual-refresh").innerHTML;
    setInterval(refreshUpdateButton, 500);
})

window.onresize = () => {
    canvas.height = canvasWrapper.clientHeight
    canvas.width = canvasWrapper.clientWidth
    heightUnit = canvas.height / lowestRank
    widthUnit = canvas.width / (rankHistory.length - 1)
    ctx = canvas.getContext("2d")
    renderGraph(rankHistory)
}

function refreshUpdateButton() {
  epoch = new Date() / 1000;
  if (epoch - lastUserUpdate < 60 * 3) {
    document.getElementById("user-update-button").innerHTML = "update cooldown - " + Math.ceil(60 * 3 - (epoch - lastUserUpdate)) + "s";
  } else {
    document.getElementById("user-update-button").innerHTML = "request update";
  }
}

function showRankInfo() {
    var closestPoint = Math.floor((mouseCanvasX / widthUnit))

    if(closestPoint >= rankHistory.length) { return }

    var xPos = closestPoint * widthUnit + widthUnit / 2
    var yPos = rankHistory[closestPoint] * heightUnit

    rankLine.style.left = xPos - 1 + "px" // -1 to account for line thickness
    rankCircle.style.left = xPos - 9 + "px"
    rankCircle.style.top = (yPos - 9) * 0.8 + "px"
    rankInfo.style.left = xPos + 20 + "px"
    rankInfo.style.top = (canvas.height - rankInfo.clientHeight) / 2  + "px"

    rankInfoGlobal.innerHTML = "<b>Global Rank:</b> #" + rankHistory[closestPoint]

    var daysAgo = rankHistory.length - closestPoint - 1
    rankInfoTime.innerHTML = daysAgo > 1 ? rankHistory.length - closestPoint - 2 + " days ago" : "today"

    rankLine.style.display = "block";
    rankCircle.style.display = "block";
    rankInfo.style.display = "block";
}

function updateRankGraphData(rankHistory) {
    lowestRank = 0
    highestRank = rankHistory[0]

    for(var i = 0; i < rankHistory.length; i++) {
        if (rankHistory[i] < highestRank) {
            highestRank = rankHistory[i]
        }
        if (rankHistory[i] > lowestRank) {
            lowestRank = rankHistory[i]
        }
    }
}

function renderGraph(rankHistory) {
    ctx.strokeStyle = "#E03535"
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(0, rankHistory[0] * heightUnit)

    for(var i = 1; i < rankHistory.length; i++) {
        var rank = rankHistory[i]
        ctx.lineTo(i * widthUnit + widthUnit / 2, rank * heightUnit)
    }

    ctx.stroke()
}

function manualRefresh() {
    getJSON("/api/update_user/" + location.pathname.split("/")[location.pathname.split("/").length - 1], setLastRefresh);
}

function setLastRefresh(_, data) {
  lastUserUpdate = data["time"];
}

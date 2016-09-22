var ws = new WebSocket("ws://" + window.location.hostname + ":9677/");

ws.onmessage = function (event) {
    var obj_update = JSON.parse(event.data);
    for (k in obj_update) {
        console.log("["+k+"]="+obj_update[k]);
    }
    var n_peers = obj_update['size']
    console.log("n_peers=" + n_peers);
    var peers = document.getElementById("peers");
    console.log("current ul-peers=" + peers.childElementCount);
    for (var i = peers.childElementCount; i < n_peers; ++i) {
        console.log("Addding LI i="+i);
        var node = document.createElement("li");
        node.appendChild(document.createTextNode(""));
        peers.appendChild(node);
    }
    console.log("#(peers)=" + peers.children.length);
    for (k in obj_update) {
        var v = obj_update[k];
        if (k == "you") {
            document.getElementById("you").innerHTML = v;
        } else if (k != "size") {
	    console.log("Setting children["+k+"]");
            peers.children[k].innerHTML = v;
        }
    }
};

bump = function () {
    console.log("bump");
    ws.send("bump");
};

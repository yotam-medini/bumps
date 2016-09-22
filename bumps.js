var ws = new WebSocket("ws://" + window.location.hostname + ":9677/");

ws.onmessage = function (event) {
    var obj_update = JSON.parse(event.data);
    for (k in obj_update) {
        console.log("["+k+"]="+obj_update[k]);
    }
    var n_clients = obj_update['size']
    console.log("n_clients=" + n_clients);
    var clients = document.getElementById("clients");
    console.log("current ul-clients=" + clients.childElementCount);
    for (var i = clients.childElementCount; i < n_clients; ++i) {
        console.log("Addding LI i="+i);
        var node = document.createElement("li");
        node.appendChild(document.createTextNode(""));
        clients.appendChild(node);
    }
    console.log("#(clients)=" + clients.children.length);
    for (k in obj_update) {
        var v = obj_update[k];
        if (k == "you") {
            document.getElementById("you").innerHTML = v;
        } else if (k != "size") {
	    console.log("Setting children["+k+"]");
            clients.children[k].innerHTML = v;
        }
    }
};

bump = function () {
    console.log("bump");
    ws.send("bump");
};

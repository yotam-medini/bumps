var ws = new WebSocket("ws://" + window.location.hostname + ":9677/");

ws.onmessage = function (event) {
    var obj_update = JSON.parse(event.data);
    var n_clients = obj_update['size']
    var clients = document.getElementById("clients");
    for (var i = clients.childElementCount; i < n_clients; ++i) {
        var node = document.createElement("li");
        node.appendChild(document.createTextNode(""));
        clients.appendChild(node);
    }
    for (var k in obj_update) {
        var v = obj_update[k];
        if (k == "you") {
            document.getElementById("you").innerHTML = v;
        } else if (k != "size") {
            clients.children[k].innerHTML = v;
        }
    }
};

bump = function () {
    ws.send("bump");
};

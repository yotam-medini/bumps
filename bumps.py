#!/usr/bin/env python3.5

import json
import sys
import time

import asyncio
import websockets

def timestr(t):
    int_t = int(t)
    gmta = time.gmtime(int_t)
    microsec = ("%.6f" % (t - int_t))[1:]
    s = "%d/%02d/%02d:%02d:%02d:%02d" % gmta[0:6]
    s += microsec
    return s

class GraceFuture(asyncio.Future):

    def __init__(self):
        asyncio.Future.__init__(self)

    def set_result_default(self, result):
        if not self.done():
            self.set_result(result)
        return self.result()

class Client:

    def __init__(self, i, ws):
        self.i = i
        self.ws = ws
        self.phase = 0;
        self.time = time.time()
        self.alive = True
        self.future = GraceFuture()

    def bump(self):
        self.phase += 1
        self.time = time.time()

    async def produce(self):
        await self.future
        result = self.future.result()
        self.future = GraceFuture()
        return result

    def future_state(self):
        f = self.future
        return "future: @%s cancelled=%s, done=%s, state=%s" % (
            hex(id(f)), f.cancelled(), f.done(), f._state)

    def send(self, message):
        self.future.set_result_default([]).append(message)

    def json_send(self, message):
        self.send(json.dumps(message))

    def hstr(self):
        address = "%s:%d" % self.ws.remote_address
        return "@%s &emsp; %s &emsp; %d" % (
            address, timestr(self.time), self.phase)

class Bumps:

    def __init__(self):
        self.rc = 0
        self.ra_to_client = {} # remote-address -> client mapping

    def clients(self):
        return self.ra_to_client.values()

    def client_publish_to_peers(self, client):
        clients = self.clients()
        peers = list(filter(lambda c: c is not client, clients))
        js_peer_message = json.dumps(
            {'size': len(self.ra_to_client), client.i: client.hstr()})
        for peer in peers:
            peer.send(js_peer_message);

    def introduce(self, client):
        clients = self.clients()
        message = dict(map(lambda c: (c.i, c.hstr()), clients))
        message['you'] = client.hstr()
        message['size'] = len(clients)
        client.json_send(message)
        self.client_publish_to_peers(client)

    def ws_message_handle(self, ws, message):
        ra = ws.remote_address
        client = self.ra_to_client.get(ra, None)
        if client is not None and message == "bump":
            client.bump()
            you_status = client.hstr()
            client.json_send({
                'you': you_status,
                'size': len(self.ra_to_client),
                client.i: you_status})
            self.client_publish_to_peers(client)

    async def ws_handler(self, ws, path):
        ra = ws.remote_address
        client = Client(len(self.ra_to_client), ws)
        self.ra_to_client[ra] = client

        producer_task = asyncio.ensure_future(client.produce())
        listener_task = asyncio.ensure_future(ws.recv())
        self.introduce(client)

        while client.alive:

            done, pending = await asyncio.wait(
                [producer_task, listener_task],
                return_when=asyncio.FIRST_COMPLETED)

            if producer_task in done:
                messages = producer_task.result()
                if ws.open:
                    for message in messages:
                        await ws.send(message)
                    producer_task = asyncio.ensure_future(client.produce())
                else:
                    client.alive = False
            if listener_task in done:
                message = listener_task.result()
                if message is None:
                    client.alive = False
                else:
                    self.ws_message_handle(ws, message)
                    listener_task = asyncio.ensure_future(ws.recv())

        del self.ra_to_client[ra]

    def run(self, host):
        start_server = websockets.serve(self.ws_handler, host, 9677)
        asyncio.get_event_loop().run_until_complete(start_server)
        asyncio.get_event_loop().run_forever()

if __name__ == '__main__':
    bumps = Bumps()
    bumps.run(sys.argv[1] if len(sys.argv) > 1 else 'localhost')
    sys.exit(bumps.rc)

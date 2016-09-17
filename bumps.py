#!/usr/bin/env python3.5

import json
import sys
import asyncio
import websockets
import time


def strnow():
    now = time.time()
    int_now = int(now)
    lta = time.localtime(int_now)
    microsec = ("%.6f" % (now - int_now))[1:]
    s = "%d/%02d/%02d:%02d:%02d:%02d" % lta[0:6]
    s += microsec
    return s

def timestr(t):
    int_t = int(t)
    gmta = time.gmtime(int_t)
    microsec = ("%.6f" % (t - int_t))[1:]
    s = "%d/%02d/%02d:%02d:%02d:%02d" % gmta[0:6]
    s += microsec
    return s

def elog(msg):
    sys.stderr.write("%s %s\n" % (strnow(), msg))

class DebugFuture(asyncio.Future):

    def __init__(self):
        asyncio.Future.__init__(self)

    def cancel(self):
        elog("DebugFuture.cancel")
        elog("Boom %d" % (1/0))
        asyncio.Future.cancel(self)
        
class Client:

    def __init__(self, i, ws):
        self.i = i
        self.ws = ws
        self.phase = 0;
        self.time = time.time()
        self.alive = True
        # self.future = asyncio.Future()
        self.future = DebugFuture()
        elog("Client.__init__: future=%s" % self.future_state())

    def bump(self):
        self.phase += 1
        self.time = time.time()

#    async def produce(self):
#        # self.future = asyncio.Future()
#        while True:
#            elog("Client.run: await future")
#            await self.future
#            result = self.future.result()
#            self.future = asyncio.Future()
#            yield result

    async def produce(self):
        elog("Client.produce: %s await future" % str(self.ws.remote_address))
        await self.future
        elog("Client.produce: %s awaited" % str(self.ws.remote_address))
        result = self.future.result()
        # self.future = asyncio.Future()
        self.future = DebugFuture()
        self.future.add_done_callback(self.future_dbg)
        elog("Client.produce: new %s" % self.future_state())
        return result

    def future_state(self):
        f = self.future
        return "future: @%s cancelled=%s, done=%s, state=%s" % (
            hex(id(f)), f.cancelled(), f.done(), f._state)

    def send(self, message):
        elog("client.send message[0x10]=%s" % message[:0x10])
        elog("client.send Before set_result: %s" % self.future_state())
        self.future.set_result(message)
        elog("client.send After set_result:  %s" % self.future_state())

    def json_send(self, message):
        elog("client.json_send message=%s" % str(message))
        self.send(json.dumps(message))

    def future_dbg(self, f):
        elog("future_dbg: f=%s %s" % (hex(id(f)), self.future_state()))

    def __str__(self):
        address = "%s:%d" % self.ws.remote_address
        return "@%s %s %d" % (address, timestr(self.time), self.phase)

    def hstr(self):
        address = "%s:%d" % self.ws.remote_address
        return "@%s &emsp; %s &emsp; %d" % (
            address, timestr(self.time), self.phase)

class Bumps:

    def __init__(self):
        self.rc = 0
        self.ra_to_client = {}
        
    def peers(self, client):
        return filter(lambda c: c is not client, self.ra_to_client.values())

    def introduce(self, client):
        elog("introduce")
        peers = list(self.peers(client))
        elog("peers: T=%s, V=%s" % (type(peers), str(peers)))
        message = dict(map(lambda c: (c.i, str(c)), peers))
        message['you'] = client.hstr()
        message['size'] = len(peers)
        elog("introduce: message=%s" % str(message))
        client.json_send(message)

    def ws_message_handle(self, ws, message):
        ra = ws.remote_address
        client = self.ra_to_client.get(ra, None)
        elog("ws_message_handle: ws=%s, message=%s" % (str(ra), message))
        if client is not None and message == "bump":
            elog("ws_message_handle: %s" % client.future_state())
            client.bump()
            client.json_send({'you': client.hstr()})
            js_peer_message = json.dumps(
                {'size': len(self.ra_to_client), client.i: str(client)})
            elog("js_peer_message=%s" % str(js_peer_message))
            map(lambda peer: peer.send(js_peer_message), self.peers(client))

    async def ws_handler(self, ws, path):
        elog("ws_handler: path=%s" % str(path))
        ra = ws.remote_address
        elog("ra=%s" % str(ra))
        client = Client(len(self.ra_to_client), ws)
        #  self.introduce(client)
        self.ra_to_client[ra] = client

        self.alive = True
        loop_count = 0

        producer_task = asyncio.ensure_future(client.produce())
        listener_task = asyncio.ensure_future(ws.recv())
        self.introduce(client)

        while client.alive:
            elog("loop_count=%d" % loop_count)
            # producer_task = asyncio.ensure_future(ClientProducer(client))


            done, pending = await asyncio.wait(
                [producer_task, listener_task],
                return_when=asyncio.FIRST_COMPLETED)
            elog("loop=%d  P=%s, L=%s" %
                 (loop_count, producer_task in done, listener_task in done))

            if producer_task in done:
                elog("producer")
                message = producer_task.result()
                elog("message=%s" % str(message))
                if ws.open:
                    await ws.send(message)
                    producer_task = asyncio.ensure_future(client.produce())
                else:
                    client.alive = False
            # else:
            #     producer_task.cancel()

            if listener_task in done:
                elog("listener: %s" % client.future_state())
                message = listener_task.result()
                if message is None:
                    client.alive = False
                else:
                    self.ws_message_handle(ws, message)
                    listener_task = asyncio.ensure_future(ws.recv())
            # else:
            #     listener_task.cancel()

            # time.sleep(1)
            loop_count += 1
        del self.ra_to_client[ra]
        elog("ws_handler: end")

    def run(self):
        elog("type(ws_handler)=%s" % str(type(self.ws_handler)))
        start_server = websockets.serve(self.ws_handler, 'localhost', 4243)
        asyncio.get_event_loop().run_until_complete(start_server)
        elog("Calling run_forever")
        asyncio.get_event_loop().run_forever()
        elog("Cannot be reached")

if __name__ == '__main__':
    bumps = Bumps()
    bumps.run()
    sys.exit(bumps.rc)



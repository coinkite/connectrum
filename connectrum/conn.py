#
#
import json, warnings, asyncio

class StratumProtocol(object):

    def __init__(self, server, reader, writer):
        '''
            Setup state needed to handle req/resp from a single Stratum server.
            Requires a transport (TransportABC) object to do the communication.
        '''
        self.sever = server

        self.reader = reader
        self.writer = writer

        self.next_id = 1
        self.inflight = {}
        self.subscriptions = {}

        asyncio.get_event_loop().create_task(self.rxer())

    async def rxer(self):
        print("rxer starts")
        while 1:
            l = await self.reader.readline()
            self.data_received(l.decode('utf-8'))

    def _send_request(self, method, params=[], callback=None):
        '''
            Send a new request to the server. Serialized the JSON and
            tracks id numbers and optional callbacks.
        '''
        # pick a new ID
        self.next_id += 1
        req_id = self.next_id

        # serialize as JSON
        msg = {'id': req_id, 'method': method, 'params': params}
        serialized = json.dumps(msg)

        # track it
        if callback:
            msg['cb'] = callback

        self.inflight[req_id] = msg

        # send it via what transport
        self.writer.write(serialized.encode('utf-8') + b'\n')
        

    def data_received(self, body):
        '''
            Decode and dispatch responses from the server.

            Transport will call this when incoming responses happen.
        '''

        try:
            msg = json.loads(body)
        except ValueError:
            self.transport.warn("Bad JSON received from server", msg)
            return

        resp_id = msg.get('id', None)
        if resp_id is None:
            self.transport.warn("Incoming server message had no ID in it", msg)
            return

        req = self.inflight.get(resp_id) or self.subscriptions.get(resp_id)

        if req is None:
            self.transport.warn("Incoming server message had unknown ID in it: %s" % resp_id)
            return

        result = msg.get('result', None)

        callback = req.get('cb', None)
        if callback:
            callback(req, resp)

        # forget about the request, if not a subscription
        r = self.inflight.pop(resp_id, None)
        if 'subscribe' in req['method'] and r:
            self.subscriptions[resp_id] = r

    class Invokation(object):
        def __init__(self, conn, here):
            self.conn = conn
            self.parts = [here]

        def __getattr__(self, name):
            self.parts.append(name)
            return self

        def __call__(self, *args, **kws):
            method = '.'.join(self.parts)
            self.conn._send_request(method, *args, **kws)

        def __repr__(self):
            return '.'.join(self.parts) + '(...)'

    def __getattr__(self, name):
        return self.Invokation(self, name)
        

if __name__ == '__main__':
    from transport import SocketTransport

    tr.connect(('erbium1.sytes.net', 50001))

    c = StratumConnection(SocketTransport())

    c.blockchain.address.get_balance(23)

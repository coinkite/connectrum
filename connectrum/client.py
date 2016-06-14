#
# Client connect to an Electrum server.
#
import json, warnings, asyncio
from protocol import StratumProtocol

class StratumClient:

    def __init__(self, server_info, proto_code='s', loop=None, onion_only=False):
        '''
            Setup state needed to handle req/resp from a single Stratum server.
            Requires a transport (TransportABC) object to do the communication.
        '''
        self.server = server_info
        self.proto_code = proto_code
        self.protocol = None

        self.next_id = 1
        self.inflight = {}
        self.subscriptions = {}

        self.loop = loop or asyncio.get_event_loop()

        # next step; call connect()

    async def connect(self):
        '''
            Start connection process.
        '''
        hostname, port, use_ssl = self.server.get_port(self.proto_code)

        transport, protocol = await self.loop.create_connection(StratumProtocol, host=hostname, port=port, ssl=use_ssl)
        if self.protocol:
            self.protocol.close()

        self.protocol = protocol
        protocol.client = self


    async def rxer(self):
        print("rxer starts")
        while 1:
            l = await self.reader.readline()
            self.data_received(l.decode('utf-8'))

    def _send_request(self, method, params=[]):
        '''
            Send a new request to the server. Serialized the JSON and
            tracks id numbers and optional callbacks.
        '''
        # pick a new ID
        self.next_id += 1
        req_id = self.next_id

        # serialize as JSON
        msg = {'id': req_id, 'method': method, 'params': params}

        # subscriptions are a Q, normal requests are a future
        if 'subscribe' in 'method':
            rv = asyncio.Queue()
            self.subscriptions[req_id] = (msg, rv)
        else:
            rv = self.loop.create_future()
            self.inflight[req_id] = (msg, rv)

        # send it via what transport, which serializes it
        self.protocol.send_data(msg)

        return rv

    def _got_response(self, msg):
        '''
            Decode and dispatch responses from the server.

            Has already been unframed and deserialized into an object.
        '''

        resp_id = msg.get('id', None)
        if resp_id is None:
            self.transport.warn("Incoming server message had no ID in it", msg)
            return

        result = msg.get('result')

        inf = self.inflight.get(resp_id) 
        if not inf:
            sub = self.subscriptions.get(resp_id)

            # append to the queue of results
            sub.put(result)
    
            return

        if inf is None:
            logger.error("Incoming server message had unknown ID in it: %s" % resp_id)
            return

        req, fut = inf
        fut.done(resp)

        # forget about the request
        self.inflight.pop(resp_id, None)

    def call(self, method, *args):
        assert '.' in method
        return self.conn._send_request(method, args)

    class Invokation(object):
        def __init__(self, conn, here):
            self.conn = conn
            self.parts = [here]

        def __getattr__(self, name):
            self.parts.append(name)
            return self

        def __call__(self, **kws):
            method = '.'.join(self.parts)
            return self.conn._send_request(method, *args)

        def __repr__(self):
            return '.'.join(self.parts) + '(...)'

    def XXX__getattr__(self, name):
    
        return self.Invokation(self, name)
        

if __name__ == '__main__':
    from transport import SocketTransport
    from svr_info import KnownServers, ServerInfo

    import logging
    logging.getLogger('connectrum').setLevel(logging.DEBUG)
    #logging.getLogger('asyncio').setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    proto_code = 't'

    if 0:
        ks = KnownServers()
        ks.from_json('servers.json')
        which = ks.select(proto_code, is_onion=False, min_prune=1000)[0]
    else:
        which = ServerInfo({
            "seen_at": 1465686119.022801,
            "ports": "t s",
            "nickname": "dunp",
            "pruning_limit": 10000,
            "version": "1.0",
            "hostname": "erbium1.sytes.net" })

    c = StratumClient(which, proto_code, loop=loop)

    fut = c.connect()

    fut2 = c.call('server.peers.subscribe')

    loop.run_until_complete(fut)
    loop.close()

    #c.blockchain.address.get_balance(23)


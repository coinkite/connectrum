#
# Client connect to an Electrum server.
#

# Runtime check for optional modules
from importlib import util as importutil
import json, warnings, asyncio, ssl
from .protocol import StratumProtocol
from . import __version__

# Check if aiosocks is present, and load it if it is.
if importutil.find_spec("aiosocks") is not None:
    import aiosocks
    have_aiosocks = True
else:
    have_aiosocks = False

from collections import defaultdict
from .exc import ElectrumErrorResponse
import logging

logger = logging.getLogger('connectrum')

class StratumClient:


    def __init__(self, loop=None):
        '''
            Setup state needed to handle req/resp from a single Stratum server.
            Requires a transport (TransportABC) object to do the communication.
        '''
        self.protocol = None

        self.next_id = 1
        self.inflight = {}
        self.subscriptions = defaultdict(list)

        # report our version, honestly; and indicate we only understand 1.4
        self.my_version_args = (f'Connectrum/{__version__}', '1.4')

        # these are valid after connection
        self.server_version = None          # 'ElectrumX 1.13.0' or similar
        self.protocol_version = None        # float(1.4) or similar

        self.actual_connection = {}

        self.ka_task = None

        self.loop = loop or asyncio.get_event_loop()

        self.reconnect = None       # call connect() first

        # next step: call connect()

    def _connection_lost(self, protocol):
        # Ignore connection_lost for old connections
        self.disconnect_callback and self.disconnect_callback(self)
        if protocol is not self.protocol:
            return

        self.protocol = None
        logger.warn("Electrum server connection lost")

        # cleanup keep alive task
        if self.ka_task:
            self.ka_task.cancel()
            self.ka_task = None

    def close(self):
        if self.protocol:
            self.protocol.close()
            self.protocol = None
        if self.ka_task:
            self.ka_task.cancel()
            self.ka_task = None


    async def connect(self, server_info, proto_code=None, *,
                            use_tor=False, disable_cert_verify=False,
                            proxy=None, short_term=False, disconnect_callback=None):
        '''
            Start connection process.
            Destination must be specified in a ServerInfo() record (first arg).
        '''
        self.server_info = server_info
        self.disconnect_callback = disconnect_callback
        if not proto_code:
             proto_code,*_ = server_info.protocols
        self.proto_code = proto_code

        logger.debug("Connecting to: %r" % server_info)

        if proto_code == 'g':       # websocket
            # to do this, we'll need a websockets implementation that
            # operates more like a asyncio.Transport
            # maybe: `asyncws` or `aiohttp`
            raise NotImplementedError('sorry no WebSocket transport yet')

        hostname, port, use_ssl = server_info.get_port(proto_code)

        if use_tor:
            if have_aiosocks:
                # Connect via Tor proxy proxy, assumed to be on localhost:9050
                # unless a tuple is given with another host/port combo.
                try:
                    socks_host, socks_port = use_tor
                except TypeError:
                    socks_host, socks_port = 'localhost', 9050

                # basically no-one has .onion SSL certificates, and
                # pointless anyway.
                disable_cert_verify = True

                assert not proxy, "Sorry not yet supporting proxy->tor->dest"

                logger.debug(" .. using TOR")

                proxy = aiosocks.Socks5Addr(socks_host, int(socks_port))
            else:
                logger.debug("Error: want to use tor, but no aiosocks module.")

        if use_ssl == True and disable_cert_verify:
            # Create a more liberal SSL context that won't
            # object to self-signed certicates. This is
            # very bad on public Internet, but probably ok
            # over Tor
            use_ssl = ssl.create_default_context()
            use_ssl.check_hostname = False
            use_ssl.verify_mode = ssl.CERT_NONE

            logger.debug(" .. SSL cert check disabled")

        async def _reconnect():
            if self.protocol: return        # race/duplicate work

            if proxy:
                if have_aiosocks:
                    transport, protocol = await aiosocks.create_connection(
                                            StratumProtocol, proxy=proxy,
                                            proxy_auth=None,
                                            remote_resolve=True, ssl=use_ssl,
                                            dst=(hostname, port))
                else:
                    logger.debug("Error: want to use proxy, but no aiosocks module.")
            else:
                transport, protocol = await self.loop.create_connection(
                                                        StratumProtocol, host=hostname,
                                                        port=port, ssl=use_ssl)

            self.protocol = protocol
            protocol.client = self

            # capture actual values used
            self.actual_connection = dict(hostname=hostname, port=int(port),
                                            ssl=bool(use_ssl), tor=bool(proxy))
            self.actual_connection['ip_addr'] = transport.get_extra_info('peername',
                                                        default=['unknown'])[0]

            # always report our version, and get server's version
            await self.get_server_version()
            logger.debug(f"Server version/protocol: {self.server_version} / {self.protocol_version}")

            if not short_term:
                self.ka_task = self.loop.create_task(self._keepalive())

            logger.debug("Connected to: %r" % server_info)

        # close whatever we had
        if self.protocol:
            self.protocol.close()
            self.protocol = None

        self.reconnect = _reconnect
        await self.reconnect()

    async def get_server_version(self):
        # fetch version strings, save them
        # - can only be done once in v1.4
        self.server_version, pv = await self.RPC('server.version', *self.my_version_args)
        self.protocol_version = float(pv)

    async def _keepalive(self):
        '''
            Keep our connect to server alive forever, with some
            pointless traffic.
        '''
        while self.protocol:
            await self.RPC('server.ping')

            # Docs now say "The server may disconnect clients that have sent
            # no requests for roughly 10 minutes" ... so use 5 minutes here
            await asyncio.sleep(5*60)


    def _send_request(self, method, params=[], is_subscribe = False):
        '''
            Send a new request to the server. Serialized the JSON and
            tracks id numbers and optional callbacks.
        '''

        if method.startswith('blockchain.address.'):
            # these methods have changed, but we can patch them
            method, params = self.patch_addr_methods(method, params)

        # pick a new ID
        self.next_id += 1
        req_id = self.next_id

        # serialize as JSON
        msg = {'id': req_id, 'method': method, 'params': params}

        # subscriptions are a Q, normal requests are a future
        if is_subscribe:
            waitQ = asyncio.Queue()
            self.subscriptions[method].append(waitQ)

        fut = asyncio.Future(loop=self.loop)

        self.inflight[req_id] = (msg, fut)

        logger.debug(" REQ: %r" % msg)

        # send it via the transport, which serializes it
        if not self.protocol:
            logger.debug("Need to reconnect to server")

            async def connect_first():
                await self.reconnect()
                self.protocol.send_data(msg)

            self.loop.create_task(connect_first())
        else:
            # typical case, send request immediatedly, response is a future
            self.protocol.send_data(msg)

        return fut if not is_subscribe else (fut, waitQ)

    def _send_batch_requests(self, requests):
        '''
            Send a new batch of requests to the server.
        '''

        full_msg = []

        for method, *params in requests:

            if method.startswith('blockchain.address.'):
                # these methods have changed, but we can patch them
                method, params = self.patch_addr_methods(method, params)

            # pick a new ID
            self.next_id += 1
            req_id = self.next_id

            # serialize as JSON
            msg = {'id': req_id, 'method': method, 'params': params}

            full_msg.append(msg)

        fut = asyncio.Future(loop=self.loop)
        first_msg = full_msg[0]

        self.inflight[first_msg['id']] = (full_msg, fut)

        logger.debug(" REQ: %r" % full_msg)

        # send it via the transport, which serializes it
        if not self.protocol:
            logger.debug("Need to reconnect to server")

            async def connect_first():
                await self.reconnect()
                self.protocol.send_data(full_msg)

            self.loop.create_task(connect_first())
        else:
            # typical case, send request immediately, response is a future
            self.protocol.send_data(full_msg)

        return fut

    def _got_response(self, msg):
        '''
            Decode and dispatch responses from the server.

            Has already been unframed and deserialized into an object.
        '''

        logger.debug("RESP: %r" % msg)

        if isinstance(msg, list):
            # we are dealing with a batch request

            inf = None
            for response in msg:
                resp_id = response.get('id', None)
                inf = self.inflight.pop(resp_id, None)
                if inf:
                    break

            if not inf:
                first_msg = msg[0]
                logger.error("Incoming server message had unknown ID in it: %s" % first_msg['id'])
                return

            # it's a future which is done now
            full_req, rv = inf

            response_map = {resp['id']: resp for resp in msg}
            results = []
            for request in full_req:
                req_id = request.get('id', None)

                response = response_map.get(req_id, None)
                if not response:
                    logger.error("Incoming server message had missing ID: %s" % req_id)

                error = response.get('error', None)
                if error:
                    logger.info("Error response: '%s'" % error)
                    rv.set_exception(ElectrumErrorResponse(error, request))

                result = response.get('result')
                results.append(result)

            rv.set_result(results)
            return

        resp_id = msg.get('id', None)

        if resp_id is None:
            # subscription traffic comes with method set, but no req id.
            method = msg.get('method', None)
            if not method:
                logger.error("Incoming server message had no ID nor method in it", msg)
                return

            # not obvious, but result is on params, not result, for subscriptions
            result = msg.get('params', None)

            logger.debug("Traffic on subscription: %s" % method)

            subs = self.subscriptions.get(method)
            for q in subs:
                self.loop.create_task(q.put(result))

            return

        assert 'method' not in msg
        result = msg.get('result')

        # fetch and forget about the request
        inf = self.inflight.pop(resp_id)
        if not inf:
            logger.error("Incoming server message had unknown ID in it: %s" % resp_id)
            return

        # it's a future which is done now
        req, rv = inf

        if 'error' in msg:
            err = msg['error']

            logger.info("Error response: '%s'" % err)
            rv.set_exception(ElectrumErrorResponse(err, req))

        else:
            rv.set_result(result)

    def RPC(self, method, *params):
        '''
            Perform a remote command.

            Expects a method name, which look like:

                blockchain.address.get_balance

            .. and sometimes take arguments, all of which are positional.

            Returns a future which will you should await for
            the result from the server. Failures are returned as exceptions.
        '''
        assert '.' in method
        #assert not method.endswith('subscribe')

        return self._send_request(method, params)

    def batch_rpc(self, requests):
        '''
            Perform a batch of remote commands.

            Expects a list of ("method name", params...) tuples, where the method name should look
            like:

                blockchain.address.get_balance

            .. and sometimes take arguments, all of which are positional.

            Returns a future which will you should await for the list of results for each command
            from the server. Failures are returned as exceptions.
        '''
        for request in requests:
            assert isinstance(request, tuple)
            method, *params = request
            assert '.' in method

        return self._send_batch_requests(requests)

    def patch_addr_methods(self, method, params):
        # blockchain.address.get_balance(addr) => blockchain.scripthash.get_balance(sh)
        from hashlib import sha256
        from binascii import b2a_hex
        try:
            from pycoin.symbols.btc import network as BTC       # bitcoin only!
        except ImportError:
            raise RuntimeError("we can patch obsolete protocol msgs, but need pycoin>=0.90")

        # convert from base58 into sha256(binary of script)?
        addr = BTC.parse(params[0])
        sh = sha256(addr.script()).digest()[::-1]

        return method.replace('.address.', '.scripthash.'), \
                    [str(b2a_hex(sh), 'ascii')]+list(params[1:])

    def subscribe(self, method, *params):
        '''
            Perform a remote command which will stream events/data to us.

            Expects a method name, which look like:
                server.peers.subscribe
            .. and sometimes take arguments, all of which are positional.

            Returns a tuple: (Future, asyncio.Queue).
            The future will have the result of the initial
            call, and the queue will receive additional
            responses as they happen.
        '''
        assert '.' in method
        assert method.endswith('subscribe')
        return self._send_request(method, params, is_subscribe=True)


if __name__ == '__main__':
    from transport import SocketTransport
    from svr_info import KnownServers, ServerInfo

    logging.basicConfig(format="%(asctime)-11s %(message)s", datefmt="[%d/%m/%Y-%H:%M:%S]")

    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    proto_code = 's'

    if 0:
        ks = KnownServers()
        ks.from_json('servers.json')
        which = ks.select(proto_code, is_onion=True, min_prune=1000)[0]
    else:
        which = ServerInfo({
            "seen_at": 1465686119.022801,
            "ports": "t s",
            "nickname": "dunp",
            "pruning_limit": 10000,
            "version": "1.0",
            "hostname": "erbium1.sytes.net" })

    c = StratumClient(loop=loop)

    loop.run_until_complete(c.connect(which, proto_code, disable_cert_verify=True, use_tor=True))

    rv = loop.run_until_complete(c.RPC('server.peers.subscribe'))
    print("DONE!: this server has %d peers" % len(rv))
    loop.close()

    #c.blockchain.address.get_balance(23)

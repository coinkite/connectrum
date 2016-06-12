import asyncio
from abc import abstractmethod
from constants import BOOTSTRAP_SERVERS
from svr_info import ServerInfo, KnownServers
from utils import logger

class TransportABC(object):
    '''
        Define methods for this abstract base class to define a low-level transport.
    '''
    # We will call this function whenever a properly-framed (JSON string) has been received.
    rx_handler = lambda self, msg:None

    # set this to be a description of the connection
    description = 'abstract'

    @abstractmethod
    def connect(self, server, **kws):
        '''
            Make a connection or fail with an exception.
            server_address would be a tuple in most cases, host+port#
        '''
        pass

    @abstractmethod
    def tx(self, body):
        '''
            Send a string (already JSON formated) over the channel to the server.
        '''
        pass

    @abstractmethod
    def warn(self, human_msg, raw_msg=None):
        '''
            Something happened that indicates the server is confused or broken
        '''
        logger.warn(human_msg)

    def __str__(self):
        return self.description

class SocketTransport(TransportABC):

    def tx(self, body):
        print("SEND: %s"  % body)
        self.s.setblocking(True)
        self.s.sendall(body + '\n') 

    def poll(self, timeout=1.0):
        # simplistic polling non-async approach here
        buf = ''

        while True:
            (rl, _, _) = select.select([self.s], [], [], timeout)

            if self.s not in rl:
                return

            self.s.setblocking(False)

            # do a 'recvall'
            while 1:
                try:
                    here = self.s.recv(4096)
                    print("RX: " + here)
                except socket.error:
                    break
                if not here: break
                buf += here

            while buf:
                pos = buf.find('}\n')
                if pos == -1: break
                self.rx_handler(buf[0:pos+1])
                buf = buf[pos:]
        
    
    
class TCPCleartext(SocketTransport):

    def connect(self, server, timeout=5):
        dest = server.get_port('t')
        self.s = socket.create_connection(dest, timeout)
        self.description = 'TCP (cleartext) to %s port %s' % dest
        

async def find_some_server():
    '''
        Search for a working server. Accepts some filtering parameters
        and will keep going until it finds one and connects to it.
        Returns a connected transport.
        - options for different search algos/approaches
    '''
    ks = KnownServers()

    ks.from_json('servers.json')

    if not ks:
        raise RuntimeError("Don't know anyone to connect to!")

    from conn import StratumProtocol

    tr = None
    for srv in ks.select('t', is_onion=False):
        print("Connecting... %s" % srv)
        host, port = srv.get_port('t')
        try:
            rs, ws = await asyncio.open_connection(host, port)
            print("Connected: %s" % srv)

            EL = StratumProtocol(srv, rs, ws)
            EL.server.peers.subscribe()
            print(peers)

            break

        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.exception("Failed to connect to: %s  (%s)" % (srv, e))
            continue


if __name__ == '__main__':

    loop = asyncio.get_event_loop()
    loop.create_task(find_some_server())
    loop.run_forever()
    loop.close()

    if 0:
        EL = find_some_server()
        print("Connected to Electrum server: %s" % EL)

        peers = EL.server.peers.subscribe()
        print(peers)

#! /usr/bin/env python3
#
# Subscribe to any message stream that the server supports.
#
import sys, asyncio, argparse, json
from connectrum.client import StratumClient
from connectrum.svr_info import ServerInfo


async def listen(conn, svr, connector, method, args, verbose=0):

    try:
        await connector
    except Exception as e:
        print("Unable to connect to server: %s" % e)
        return -1

    print("\nConnected to: %s\n" % svr)

    if verbose:
        donate = await conn.RPC('server.donation_address')
        if donate:
            print("Donations: " + donate)

        motd = await conn.RPC('server.banner')
        print("\n---\n%s\n---"  % motd)

    print("\nMethod: %s" % method)

    fut, q = conn.subscribe(method, *args)
    print(json.dumps(await fut, indent=1))
    while 1:
        result = await q.get()
        print(json.dumps(result, indent=1))
    


def main():
    parser = argparse.ArgumentParser(description='Subscribe to BTC events')
    parser.add_argument('method', 
                        help='"blockchain.headers.subscribe" or similar')
    parser.add_argument('args', nargs="*", default=[],
                        help='Arguments for method')
    parser.add_argument('--server', default='cluelessperson.com',
                        help='Hostname of Electrum server to use')
    parser.add_argument('--protocol', default='s',
                        help='Protocol code: t=TCP Cleartext, s=SSL, etc')
    parser.add_argument('--port', default=None,
                        help='Port number to override default for protocol')
    parser.add_argument('--tor', default=False, action="store_true",
                        help='Use local Tor proxy to connect')

    args = parser.parse_args()

    # convert to our datastruct about servers.
    svr = ServerInfo(args.server, args.server,
                    ports=((args.protocol+str(args.port)) if args.port else args.protocol))

    loop = asyncio.get_event_loop()  

    conn = StratumClient()
    connector = conn.connect(svr, args.protocol, use_tor=svr.is_onion, disable_cert_verify=True)

    loop.run_until_complete(listen(conn, svr, connector, args.method, args.args))

    loop.close()

if __name__ == '__main__':
    main()
    
# EOF

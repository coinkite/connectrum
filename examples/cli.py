#! /usr/bin/env python3
#
# Provide an interactive command line for sending
# commands to an Electrum server.
#
# TODO: finish this with interactive readline
#
import sys, asyncio, argparse, json
from connectrum.client import StratumClient
from connectrum.svr_info import ServerInfo
from connectrum import ElectrumErrorResponse
import logging

logging.basicConfig(level=logging.INFO)
#logging.getLogger('connectrum').setLevel(level=logging.DEBUG)

async def interact(conn, svr, connector, method, args, verbose=False):

    try:
        await connector
    except Exception as e:
        print("Unable to connect to server: %s" % e)
        return -1

    print("\nConnected to: %s" % svr)
    print("Server version: %s" % conn.server_version)
    print("Server protocol: %s\n" % conn.protocol_version)

    if verbose:
        donate = await conn.RPC('server.donation_address')
        if donate:
            print("Donations: " + donate)

        motd = await conn.RPC('server.banner')
        print("\n---\n%s\n---"  % motd)

    # XXX TODO do a simple REPL here

    if method:
        print("\nMethod: %s" % method)

    # risky type cocerce here
    args = [(int(i) if i.isdigit() else i) for i in args]

    try:
        rv = await conn.RPC(method, *args)
        print(json.dumps(rv, indent=1))
    except ElectrumErrorResponse as e:
        print(e)

    conn.close()


def main():
    parser = argparse.ArgumentParser(description='Interact with an electrum server')
    parser.add_argument('method', default=None,
                        help='"blockchain.numblocks.subscribe" or similar')
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

    import logging

    # convert to our datastruct about servers.
    svr = ServerInfo(args.server, args.server,
                    ports=((args.protocol+str(args.port)) if args.port else args.protocol))

    loop = asyncio.get_event_loop()  

    conn = StratumClient()
    connector = conn.connect(svr, args.protocol, use_tor=svr.is_onion, disable_cert_verify=True, short_term=True)

    loop.run_until_complete(interact(conn, svr, connector, args.method, args.args))

    loop.close()

if __name__ == '__main__':
    main()
    
# EOF

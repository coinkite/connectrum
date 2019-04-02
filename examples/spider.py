#! /usr/bin/env python3
#
# Find all Electrum servers, everywhere... It will connect to one at random (from
# a hard-coded list) and then expand it's list of peers based on what it sees
# at each server.
#
# THIS IS A DEMO PROGRAM ONLY. It would be anti-social to run this frequently or
# as part of any periodic task.
#
import sys, asyncio, argparse
from connectrum.client import StratumClient
from connectrum.svr_info import KnownServers

ks = KnownServers()

connected = set()
failed = set()

async def probe(svr, proto_code, use_tor):
    conn = StratumClient()

    try:
        await conn.connect(svr, proto_code, use_tor=(svr.is_onion or use_tor), short_term=True)
    except:
        failed.add(str(svr))
        return None

    peers, _ = conn.subscribe('server.peers.subscribe')

    peers = await peers
    print("%s gave %d peers" % (svr, len(peers)))

    connected.add(str(svr))

    # track them all.
    more = ks.add_peer_response(peers)

    if more:
        print("found %d more servers from %s: %s" % (len(more), svr, ', '.join(more)))
    

    conn.close()

    return str(svr)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Interact with an electrum server')

    parser.add_argument('servers', default=[], metavar="server_list.json", nargs='*',
                        help='JSON file containing server details')
    parser.add_argument('--protocol', default='t', choices='ts',
                        help='Protocol code: t=TCP Cleartext, s=SSL, etc')
    parser.add_argument('--tor', default=False, action="store_true",
                        help='Use local Tor proxy to connect (localhost:9150)')
    parser.add_argument('--onion', default=None, action="store_true",
                        help='Select only servers operating an .onion name')
    parser.add_argument('--irc', default=False, action="store_true",
                        help='Use IRC channel to find servers')
    parser.add_argument('--output', default=None,
                        help='File to save resulting server list into (JSON)')
    parser.add_argument('--timeout', default=30, type=int,
                        help='Total time to take (overall)')

    args = parser.parse_args()

    if args.irc:
        print("Connecting to freenode #electrum... (slow, be patient)")
        ks.from_irc()

    for a in args.servers:
        ks.from_json(a)

    #ks.from_json('../connectrum/servers.json')

    if not ks:
        print("Please use --irc option or a list of servers in JSON on command line")
        sys.exit(1)

    print("%d servers are known to us at start" % len(ks))

    loop = asyncio.get_event_loop()  

    # cannot reach .onion if not using Tor; so filter them out
    if not args.tor:
        args.onion = False

    candidates = ks.select(protocol=args.protocol, is_onion=args.onion)
    print("%d servers are right protocol" % len(candidates))

    all_done = asyncio.wait([probe(i, args.protocol, args.tor) for i in candidates],
                                            timeout=args.timeout)

    loop.run_until_complete(all_done)
    loop.close()

    if not connected:
        print("WARNING: did not successfully connect to any existing servers!")
    else:
        print("%d servers connected and answered correctly" % len(connected))

    if failed:
        print("%d FAILURES: " % len(failed))
        for i in failed:
            print('  %s' % i)

    print("%d servers are now known" % len(ks))
    if 0:
        for i in ks.values():
            print('  %s  [%s]' % (i.hostname, ' '.join(i.protocols)))

    if args.output:
        ks.save_json(args.output)
    
# EOF

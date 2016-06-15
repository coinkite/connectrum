#! /usr/bin/env python3
#
# Find all Electrum servers, everywhere... It will connect to one at random (from
# a hard-coded list) and then expand it's list of peers based on what it sees
# at each server.
#
# THIS IS A DEMO PROGRAM ONLY. It would be anti-social to run this frequently or
# as part of any periodic task.
#
import sys, asyncio
from connectrum.client import StratumClient
from connectrum.svr_info import KnownServers

ks = KnownServers()

connected = set()
failed = set()

async def probe(svr, proto_code):
    conn = StratumClient()

    try:
        await conn.connect(svr, proto_code, use_tor=svr.is_onion)
    except:
        failed.add(str(svr))
        return None

    peers = await conn.RPC('server.peers.subscribe')

    print("%s gave %d peers" % (svr, len(peers)))

    if len(peers) > 56:
        print("Peers: %r" % peers)

    connected.add(str(svr))

    # track them all.
    more = ks.add_peer_response(peers)

    if more:
        print("found %d more servers from %s: %s" % (len(more), svr, ', '.join(more)))

    return str(svr)


if __name__ == '__main__':

    proto_code = 't'

    if '--irc' in sys.argv:
        print("connecting to freenode #electrum... (30 seconds)")
        ks.from_irc()

    for a in sys.argv:
        if a.endswith('.json'):
            ks.from_json(a)

    ks.from_json('../connectrum/servers.json')

    print("%d servers are known to us at start" % len(ks))

    loop = asyncio.get_event_loop()  

    candidates = ks.select(proto_code)
    print("%d servers are right protocol" % len(candidates))

    all_done = asyncio.wait([probe(i, proto_code) for i in candidates], timeout=30)

    loop.run_until_complete(all_done)
    loop.close()

    print("%d servers now known" % len(ks))

    ks.save_json('complete.json')
    
# EOF

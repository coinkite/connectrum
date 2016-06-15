#
# Be a simple bitcoin block explorer. Just an toy example!
#
import re, aiohttp, json, textwrap
from aiohttp import web
from aiohttp.web import HTTPFound, Response
from connectrum.client import StratumClient
from connectrum.svr_info import KnownServers


def linkage(n):
    return '<a href="/%s/%s"><code>%s</code></a>' % (
            ('txn' if len(n) == 64 else 'addr'), n, n)
        

async def homepage(request):
    conn = request.app['conn']
    t='''
        <link rel="stylesheet" href="http://yui.yahooapis.com/pure/0.6.0/pure-min.css" />
        <style>
            body { margin: 20px; }
        </style>
        <body>
        <h1>Explore Bitcoin</h1>
    '''
    t += "<h2>%s</h2>" % conn.server_info 

    donate = await conn.RPC('server.donation_address')
    t += '<p>Donations: ' + linkage(donate)

    motd = await conn.RPC('server.banner')
    t += '</p><pre>\n%s\n</pre>' % motd

    t += '''
        <form method=POST action="/">
            <input name='q' style="width: 50%" placeholder="Txn hash / address / etc"></input>
    '''

    return Response(content_type='text/html', text=t)

async def search(request):
    query = (await request.post())['q'].strip()

    if not (3 <= len(query) <= 200):
        raise HTTPFound('/')

    if len(query) == 64:
        # assume it's a hash of block or txn
        raise HTTPFound('/txn/'+query.lower())
    elif query[0] in '13mn':
        # assume it'a payment address
        raise HTTPFound('/addr/'+query)
    else:
        return Response(text="Can't search for that")


async def address_page(request):
    addr = request.match_info['addr']
    conn = request.app['conn']

    t = '<h1><code>%s</code></h1>' % addr

    for method in ['blockchain.address.get_balance',
                    'blockchain.address.get_mempool',
                    'blockchain.address.get_proof',
                    'blockchain.address.listunspent']:
        # get a balance, etc.
        resp = await conn.RPC(method, addr)
        t += '<h3><tt>%s</tt></h3><pre>%s</pre>' % (method, json.dumps(resp, indent=2))
    
    return Response(content_type='text/html', text=t)

async def transaction_page(request):
    txn_hash = request.match_info['txn_hash']
    conn = request.app['conn']

    t = '<h2><code>%s</code></h2>' % txn_hash

    for method in ['blockchain.transaction.get']:
        resp = await conn.RPC(method, txn_hash)
        t += '<h3><tt>%s</tt></h3><pre>' % method
        if isinstance(resp, str):
            t += '\n'.join(textwrap.wrap(resp))
        else:
            t += json.dumps(resp, indent=2)
        t += '</pre>'
    
    return Response(content_type='text/html', text=t)
    


if __name__ == "__main__":
    app = web.Application()
    app.router.add_route('GET', '/', homepage)
    app.router.add_route('POST', '/', search)
    app.router.add_route('GET', '/addr/{addr}', address_page)
    app.router.add_route('GET', '/txn/{txn_hash}', transaction_page)

    ks = KnownServers()
    ks.from_json('../connectrum/servers.json')
    servers = ks.select(is_onion=False, min_prune=1000)

    assert servers, "Need some servers to talk to."

    # pick a random server
    app['conn'] = conn = StratumClient()
    app.loop.create_task(conn.connect(servers[0], disable_cert_verify=True))

    web.run_app(app)

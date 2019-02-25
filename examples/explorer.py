#!/usr/bin/env python3
#
# Be a simple bitcoin block explorer. Just an toy example!
#
# Limitations:
# - picks a random Electrum server each time it starts (which is a crapshoot)
# - displays nothing interesting for txn
# - does not do block hash numbers, only by height
# - inline html is terrible
# - ugly
#
import re, aiohttp, json, textwrap, asyncio, sys
from aiohttp import web
from aiohttp.web import HTTPFound, Response
from connectrum.client import StratumClient
from connectrum.svr_info import KnownServers, ServerInfo
from connectrum import ElectrumErrorResponse

top_blk = 6666

HTML_HDR = '''
    <link rel="stylesheet" href="http://yui.yahooapis.com/pure/0.6.0/pure-min.css" />
    <style>
        body { margin: 20px; }
    </style>
    <body>
    <a href="/"><h1>Explore Bitcoin</h1></a>
'''

def linkage(n, label=None):
    n = str(n)
    if len(n) == 64:
        t = 'txn'
    elif len(n) < 7:
        t = 'blk'
    else:
        t = 'addr'

    return '<a href="/%s/%s"><code>%s</code></a>' % (t, n, label or n)
        

async def homepage(request):
    conn = request.app['conn']
    t = HTML_HDR
    t += "<h2>%s</h2>" % conn.server_info 

    # NOTE: only a demo program would do all these remote server
    # queries just to display the hompage...

    donate = await conn.RPC('server.donation_address')

    motd = await conn.RPC('server.banner')
    t += '<pre style="font-size: 50%%">\n%s\n</pre><hr/>' % motd

    t += '<p>Donations: %s</p>' % linkage(donate)
    t += '</p><p>Top block: %s</p>' % linkage(top_blk['block_height'])


    t += '''
        <form method=POST action="/">
            <input name='q' style="width: 50%" placeholder="Txn hash / address / etc"></input>
    '''

    return Response(content_type='text/html', text=t)

async def call_and_format(conn, method, *args):
    # call a method and format up the response nicely

    t = ''
    try:
        resp = await conn.RPC(method, *args)
    except ElectrumErrorResponse as e:
        response, req = e.args
        t += "<h3>Server Error</h3><pre>%s\n%s</pre>" % (response, req)
        return t

    if isinstance(resp, str):
        here = '\n'.join(textwrap.wrap(resp))
    else:
        here = json.dumps(resp, indent=2)

    # simulate <pre> somewhat
    here = here.replace('\n', '<br/>')
    here = here.replace('<br/> ', '<br/>&nbsp;')

    # link to txn
    here = re.sub(r'"([a-f0-9]{64})"', lambda m: linkage(m.group(1)), here)
    # TODO: link to blk numbers
    

    t += '<h3><tt>%s</tt></h3><code>' % method
    t += here
    t += '</code>'

    return t

async def search(request):
    query = (await request.post())['q'].strip()

    if not (1 <= len(query) <= 200):
        raise HTTPFound('/')

    if len(query) <= 7:
        raise HTTPFound('/blk/'+query.lower())
    elif len(query) == 64:
        # assume it's a hash of block or txn
        raise HTTPFound('/txn/'+query.lower())
    elif query[0] in '13mn':
        # assume it'a payment address
        raise HTTPFound('/addr/'+query)
    else:
        return Response(text="Can't search for that")


async def address_page(request):
    # address summary by bitcoin payment addr
    addr = request.match_info['addr']
    conn = request.app['conn']

    t = HTML_HDR
    t += '<h1><code>%s</code></h1>' % addr

    for method in ['blockchain.address.get_balance',
                    #'blockchain.address.get_status',
                    'blockchain.address.get_mempool',
                    #'blockchain.address.get_proof',
                    'blockchain.address.listunspent']:
        # get a balance, etc.
        t += await call_and_format(conn, method, addr)
    
    return Response(content_type='text/html', text=t)

async def transaction_page(request):
    # transaction by hash
    txn_hash = request.match_info['txn_hash']
    conn = request.app['conn']

    t = HTML_HDR
    t += '<h2><code>%s</code></h2>' % txn_hash

    for method in ['blockchain.transaction.get']:
        t += await call_and_format(conn, method, txn_hash)
    
    return Response(content_type='text/html', text=t)
    
async def block_page(request):
    # blocks by number (height)
    height = int(request.match_info['height'], 10)
    conn = request.app['conn']

    t = HTML_HDR
    t += '<h2>Block %d</h2>' % height

    for method in ['blockchain.block.get_header']:
        t += await call_and_format(conn, method, height)

    t += '<hr/><p>%s &nbsp;&nbsp; %s</p>' % (linkage(height-1, "PREV"), linkage(height+1, "NEXT"))
    
    return Response(content_type='text/html', text=t)

async def startup_code(app):
    # pick a random server
    app['conn'] = conn = StratumClient()
    try:
        await conn.connect(el_server, disable_cert_verify=True,
                                use_tor=('localhost', 9150) if el_server.is_onion else False)
    except Exception as exc:
        print("unable to connect: %r" % exc)
        sys.exit()

    print("Connected to electrum server: {hostname}:{port} ssl={ssl} tor={tor} ip_addr={ip_addr}".format(**conn.actual_connection))

    # track top block
    async def track_top_block():
        global top_blk
        fut, Q = conn.subscribe('blockchain.headers.subscribe')
        top_blk = await fut
        while 1:
            top_blk = max(await Q.get())
            print("new top-block: %r" % (top_blk,))

    app.loop.create_task(track_top_block())


if __name__ == "__main__":
    app = web.Application()
    app.router.add_route('GET', '/', homepage)
    app.router.add_route('POST', '/', search)
    app.router.add_route('GET', '/addr/{addr}', address_page)
    app.router.add_route('GET', '/txn/{txn_hash}', transaction_page)
    app.router.add_route('GET', '/blk/{height}', block_page)

    if 0:
        ks = KnownServers()
        ks.from_json('../connectrum/servers.json')
        servers = ks.select(is_onion=False, min_prune=1000)

        assert servers, "Need some servers to talk to."
        el_server = servers[0]
    else:
        el_server = ServerInfo('hardcoded', sys.argv[-1], 's')
        #el_server = ServerInfo('hardcoded', 'daedalus.bauerj.eu', 's')

    loop = asyncio.get_event_loop()
    loop.create_task(startup_code(app))

    web.run_app(app)

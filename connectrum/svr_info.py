#
# Store information about servers. Filter and select based on their protocol support, etc.
#
import time, random, json
from constants import DEFAULT_PORTS


class ServerInfo(dict):
    '''
        Information to be stored on a server. Based on IRC data that is published.
    '''
    FIELDS = ['nickname', 'hostname', 'ports', 'version', 'pruning_limit', 'seen_at']

    def __init__(self, nickname_or_dict, hostname=None, ports=None,
                        version=None, pruning_limit=None, ip_addr=None):

        if not hostname and not ports:
            # promote a dict, or similar
            super(ServerInfo, self).__init__(nickname_or_dict)
            return

        self['nickname'] = nickname_or_dict or None
        self['hostname'] = hostname
        self['ip_addr'] = ip_addr or None

        # for ports, take
        # - a number (int), assumed to be TCP port, OR
        # - a list of codes
        # - a string to be split apart
        # - keep version and pruning limit separate
        #
        if isinstance(ports, int):
            ports = 't%d' % ports
        elif ' ' in ports:
            plist = []

            for p in ports.split(' '):
                if p[0] == 'v':
                    version = p[1:]
                elif p[0] == 'p':
                    pruning_limit = int(p[1:])
                else:
                    plist.append(p)

            ports = plist
            
        assert ports, "Must have at least one port/protocol"
        assert not isinstance(ports, str), "Ports is a list of strings"

        self['ports'] = ports
        self['version'] = version
        self['pruning_limit'] = int(pruning_limit or 0)

        self['seen_at'] = time.time()

    @classmethod
    def from_dict(cls, d):
        n = d.pop('nickname')
        h = d.pop('hostname')
        p = d.pop('ports')
        rv = cls(n, h, p)
        rv.update(d)
        return rv


    @property
    def protocols(self):
        rv = set(self['ports'])
        assert 'p' not in rv, 'pruning limit got in there'
        assert 'v' not in rv, 'version got in there'
        return rv

    @property
    def pruning_limit(self):
        return self.get('pruning_limit', 100)

    def get_port(self, for_protocol):
        '''
            Return (hostname, port number, ssl) pair for the protocol.
            Assuming only one port per host.
        '''
        assert len(for_protocol) == 1, "expect single letter code"

        rv = [i[0] for i in self['ports'] if i[0] == for_protocol]
        if not rv:
            return None

        port = DEFAULT_PORTS[for_protocol] if len(rv) == 1 else int(rv[1:])

        use_ssl = for_protocol in ('s', 'g')

        return self['hostname'], port, use_ssl
        

    @property
    def is_onion(self):
        return self['hostname'].lower().endswith('.onion')

    def __repr__(self):
        return '<ServerInfo {hostname} nick={nickname} ports="{ports}" v={version} prune={pruning_limit}>'\
                                        .format(**self)

    def __str__(self):
        return '{hostname} [{ports}]'.format(**self)

class KnownServers(dict):
    '''
        Store a list of known servers and their port numbers, etc.

        - can add single entries
        - can read from a CSV for seeding/bootstrap
        - can read from IRC channel to find current hosts
    '''

    def from_json(self, fname):
        '''
            Read contents of a CSV containing a list of servers.
        '''
        with open(fname, 'rt') as fp:
            for row in json.load(fp):
                nn = ServerInfo.from_dict(row)
                self[nn['hostname'].lower()] = nn

    def from_irc(self, irc_nickname=None, irc_password=None):
        '''
            Connect to the IRC channel and find all servers presently connected.

            Slow; takes 30+ seconds but authoritative and current.
        '''
        from findall import IrcListener
        
        # connect and fetch current set of servers who are
        # on #electrum channel at freenode

        bot = IrcListener(irc_nickname=irc_nickname, irc_password=irc_password)
        results = bot.loop.run_until_complete(bot.collect_data())
        bot.loop.close()

        # merge by nick name
        self.update(results)

    def add_single(self, hostname, ports, nickname=None, **kws):
        '''
            Explicitly add a single entry.
            Hostname is a FQDN and ports is either a single int (assumed to be TCP port)
            or Electrum protocol/port number specification with spaces in between.
        '''
        nickname = nickname or hostname

        self[hostname] = ServerInfo(nickname, hostname, ports, **kws)

    def add_peer_response(cls, response_list):
        # Update with response from Stratum (lacks the nickname value tho):
        #
        #      "91.63.237.12",
        #      "electrum3.hachre.de",
        #      [ "v1.0", "p10000", "t", "s" ]
        #
        for parms in response_list:
            ip_addr, hostname, ports = params

            if ip_addr == hostname:
                ip_addr = None

            g = self.get(hostname.lower())
            nickname = g['nickname'] if g else None

            self[hostname] = ServerInfo(nickname, host, ports, ip_addr=ip_addr)

    def save_json(self, fname='servers.json'):
        '''
            Write out to a CSV file.
        '''
        rows = sorted(self.keys())
        with file(fname, 'wb') as fp:
            json.dump(fp, [self[k] for k in rows], indent=2)

    def dump(self):
        return '\n'.join(repr(i) for i in self.values())

    def select(self, protocol, is_onion=False, min_prune=1):
        '''
            Find all servers with indicated protocol support. Shuffled.

            Filter by TOR support, and pruning level.
        '''
        lst = [i for i in self.values() 
                            if (protocol in i.protocols)
                                and (i.is_onion == is_onion)
                                and (i.pruning_limit >= min_prune) ]

        random.shuffle(lst)

        return lst
        

if __name__ == '__main__':

    ks = KnownServers()

    #ks.from_json('servers.json')
    ks.from_irc()

    #print (ks.dump())

    from constants import PROTOCOL_CODES

    print ("%3d: servers in total" % len(ks))

    for tor in [False, True]:
        for pp in PROTOCOL_CODES.keys():
            ll = ks.select(pp, is_onion=tor)
            print ("%3d: %s" % (len(ll), PROTOCOL_CODES[pp] + (' [TOR]' if tor else '')))

# EOF

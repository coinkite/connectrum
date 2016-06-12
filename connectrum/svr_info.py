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

    def __init__(self, nickname, hostname, ports, version=None, pruning_limit=None):
        self['nickname'] = nickname
        self['hostname'] = hostname
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
        rv = set(i[0] for i in self['ports'].split())
        assert 'p' not in rv, 'pruning limit got in there'
        assert 'v' not in rv, 'version got in there'
        return rv

    @property
    def pruning_limit(self):
        return self.get('pruning_limit', 100)

    def get_port(self, for_protocol):
        '''
            Return (hostname, port number) pair for the protocol.
            Assuming only one port per host.
        '''
        assert len(for_protocol) == 1, "expect single letter code"

        rv = [i[0] for i in self['ports'].split() if i[0] == for_protocol]
        if not rv:
            return None

        port = DEFAULT_PORTS[for_protocol] if len(rv) == 1 else int(rv[1:])

        return self['hostname'], port
        

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
                self[nn['nickname']] = nn

    def from_irc(self, irc_nickname=None, irc_password=None):
        '''
            Connect to the IRC channel and find all servers presently connected.

            Slow; takes 30+ seconds but authoritative and current.
        '''
        from findall import IrcSampler

        th = IrcSampler(irc_nickname, irc_password)
        th.run()

        # merge by nick name
        self.update(th.results)

    def add_single(self, hostname, ports, nickname=None, **kws):
        '''
            Explicitly add a single entry.
            Hostname is a FQDN and ports is either a single int (assumed to be TCP port)
            or Electrum protocol/port number specification with spaces in between.
        '''
        nickname = nickname or hostname
        if isinstance(ports, int):
            ports = 't%d' % ports

        self[nickname] = ServerInfo(nickname, hostname, ports, **kws)

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

    ks.from_json('servers.json')
    #ks.from_irc('testing')

    #print (ks.dump())

    from constants import PROTOCOL_CODES

    print ("%3d: servers in total" % len(ks))

    for tor in [False, True]:
        for pp in PROTOCOL_CODES.keys():
            ll = ks.select(pp, is_onion=tor)
            print ("%3d: %s" % (len(ll), PROTOCOL_CODES[pp] + (' [TOR]' if tor else '')))

# EOF

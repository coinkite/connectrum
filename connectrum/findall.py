# XXX rewrite for irc3 and python3 and asyncio!
# or better? https://github.com/numberoverzero/bottom

#!/usr/bin/env python
#
# Heavily based on ircthread.py from electrum.
#
# Copyright(C) 2016 Opendime
# Copyright(C) 2011-2016 Thomas Voegtlin
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import re
import time
import socket
import random
import ssl
import threading
import time
import csv
import Queue
import irc.client
from utils import logger
from srv_info import ServerInfo
from collections import OrderedDict
from pprint import pformat
        

class IrcSampler(threading.Thread):

    def __init__(self, nick=None, password=None):
        threading.Thread.__init__(self)

        self.nick = nick or 'S%dN' % random.randint(1E11, 1E12)
        self.password = password
        self.who_queue = Queue.Queue()
        self.results = OrderedDict()
        self.stopped = False
        self.daemon = True
        self.state = 'init'

    def getname(self):
        return "Client at " + self.nick

    def start(self, queue):
        self.queue = queue
        self.state = 'started'
        threading.Thread.start(self)

    def on_connect(self, connection, event):
        connection.join("#electrum")
        self.state = 'connected'
        logger.info("Connected")

    def on_join(self, connection, event):
        self.state = 'joined'
        logger.info("Joined channel")
        m = re.match("(E_.*)!", event.source)
        if m:
            self.who_queue.put((connection, m.group(1)))

    def on_disconnect(self, connection, event):
        self.state = 'disconnected'
        logger.info("Disconnected from server")
        raise StopIteration

    def on_who(self, connection, event):
        # received a response from our whois request
        line = str(event.arguments[6]).split()

        nick = event.arguments[4]
        nick = nick[2:] if nick[0:2] == 'E_' else nick
        host = line[1]

        pl, version, ports = None, None, []
        for p in line[2:]:
            if p[0] == 'v':
                version = p[1:]
            elif p[0] == 'p':
                pl = int(p[1:])
            else:
                ports.append(p)

        #logger.debug("Found: '%s' at %s with ports %s" % (nick, host, ' '.join(ports)))
        self.results[nick] = ServerInfo(nick, host, ' '.join(ports),
                                                version=version, pruning_limit=pl)

    def on_name(self, connection, event):
        for s in event.arguments[2].split():
            if s.startswith("E_"):
                self.who_queue.put((connection, s))

    def who_thread(self):
        while not self.stopped:
            try:
                connection, s = self.who_queue.get(timeout=3)
            except Queue.Empty:
                if self.results:
                    #print pformat(dict(self.results))
                    logger.info("Got %d results" % len(self.results))
                    self.status = 'done'

                    self.connection.quit('Thanks')
                    break

                continue

            #print "WHO: " + s
            connection.who(s)
            #time.sleep(0.10)

        logger.info("Who thread stops")

    def run(self):
        # avoid UnicodeDecodeError using LenientDecodingLineBuffer
        irc.client.ServerConnection.buffer_class = irc.buffer.LenientDecodingLineBuffer
        logger.info("Start IRC client connection")

        t = threading.Thread(target=self.who_thread)
        t.daemon = True
        t.start()

        client = irc.client.Reactor()

        try:
            #bind_address = (self.irc_bind_ip, 0) if self.irc_bind_ip else None
            #ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket, bind_address=bind_address)
            #c = client.server().connect('irc.freenode.net', 6697, self.nick, self.password, ircname=self.nick, connect_factory=ssl_factory)
            c = client.server().connect('irc.freenode.net', 6667, self.nick, self.password, ircname=self.nick) 
            self.state = 'connecting'
        except irc.client.ServerConnectionError:
            logger.exception('irc connect')
            raise
            #self.state = 'disconnected'
            #time.sleep(10)
            #continue

        logger.info("Connecting to Freenode")

        c.add_global_handler("welcome", self.on_connect)
        c.add_global_handler("join", self.on_join)
        #c.add_global_handler("quit", self.on_quit)
        #c.add_global_handler("kick", self.on_kick)
        c.add_global_handler("whoreply", self.on_who)
        c.add_global_handler("namreply", self.on_name)
        c.add_global_handler("disconnect", self.on_disconnect)
        c.set_keepalive(60)

        self.connection = c
        try:
            client.process_forever()
        except StopIteration:
            pass
        except KeyboardInterrupt:
            raise

        t.stop()

        logger.info("Done with IRC")

if __name__ == '__main__':
    '''
        When run on the command line, this program connects to IRC
        and downloads a list of all servers there and writes into
        a file in the current directory.
    '''

    import logging
    logger.setLevel(logging.DEBUG)

    th = IrcSampler()
    th.run()

    rows = sorted(th.results.keys())

    import csv
    with file('servers.csv', 'wb') as fp:
        c = csv.DictWriter(fp, ServerInfo.FIELDS)
        c.writeheader()
        c.writerows([th.results[k] for k in rows])



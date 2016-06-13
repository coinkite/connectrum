#
#
#
import bottom, random, time
from queue import Queue
import logging

from utils import logger
logging.getLogger('bottom').setLevel(logging.DEBUG)

#bot = bottom.Client(host='irc.freenode.net', port=6697, ssl=True)
bot = bottom.Client(host='irc.freenode.net', port=6667, ssl=False)
NICK = 'XC%d' % random.randint(1E11, 1E12)

worklist = Queue()

@bot.on('CLIENT_CONNECT')
def connect(**kwargs):
    print("Connected")
    bot.send('NICK', nick=NICK)
    bot.send('USER', user=NICK, realname='Connectrum Client')
    # long delay here as it does an failing Ident probe (10 seconds min)
    bot.send('JOIN', channel='#electrum')
    #bot.send('WHO', mask='E_*')

@bot.on('PING')
def keepalive(message, **kwargs):
    bot.send('PONG', message=message)

@bot.on('JOIN')
def joined(nick=None, **kwargs):
    # happens when we or someone else joins the channel
    # I have joined; takes 10 seconds it seems.
    print('Joined: %r' % kwargs)

    bot.send('WHO', mask=nick)
    #if nick == NICK:
    #bot.send('WHOIS', mask='E_*')

    if nick.startswith('E_'):
        worklist.add(nick)

@bot.on('RPL_NAMREPLY')
def got_users(users, **):
    # after successful join to channel, we are given a list of 
    # users on the channel. Happens a few times for busy channels.
    #print('WHOIS resp a=%r k=%r' % (a, k))
    print('Users: %s' % users)

@bot.on('RPL_ENDOFNAMES')
def got_eonames(*a, **k):
    print('RPL_ENDOFNAMES a=%r k=%r' % (a, k))

@bot.on("privmsg")
def echo(*a, **k):
    print('PRIVMSG: a=%r k=%r' % (a, k))



@bot.on("client_disconnect")
async def reconnect(**kwargs):
    # Trigger an event that may cascade to a client_connect.
    # Don't continue until a client_connect occurs, which may be never.

    print("Disconnected")

    # Note that we're not in a coroutine, so we don't have access
    # to await and asyncio.sleep
    time.sleep(3)

    # After this line we won't necessarily be connected.
    # We've simply scheduled the connect to happen in the future
    bot.loop.create_task(bot.connect())

    print("Reconnect scheduled.")


if __name__ == '__main__':
    bot.loop.create_task(bot.connect())
    bot.loop.run_forever()


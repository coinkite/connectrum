Connectrum
----------

Stratum (electrum-server) Client Protocol library
=================================================

Uses python3 to be a client to the Electrum server network. It makes heavy use of
`asyncio` module and newer Python 3 keywords such as `await` and `async`.

For non-server applications, you can probably find all you need
already in the standard Electrum code and command line.

Features
========

- can connect via Tor, SSL, proxied or directly
- filter lists of peers by protocol, `.onion` name
- manage lists of Electrum servers in simple JSON files.
- fully asynchronous design, so can connect to multiple at once
- a number of nearly-useful examples provided
- any  call to methods `blockchain.address.*` is converted into the more
  modern equivilent `blockchain.scripthash.*` transparently. Requires pycoin module.

Examples
========

In `examples` you will find a number little example programs.

- `cli.py` send single commands, plan is to make this an interactive REPL
- `subscribe.py` stream changes/events for an address or blocks.
- `explorer.py` implements a simplistic block explorer website
- `spider.py` find all Electrum servers recursively, read/write results to JSON

Version History
===============

- **0.8.2** Indicate we support protocol version 1.4.2, `StratumClient.protocol_version` now string
- **0.8.1** Handle protocol version reporting correctly, use 'ping' msg. (Says we are 1.4)
- **0.8.0** Support for ElectrumX protocol 1.4 with some helpers to restore useful functions.
- **0.7.4** Add `actual_connection` atrribute on `StratumClient` with some key details
- **0.7.3** Not sure
- **0.7.2** Bugfix: port numbers vs. protocols
- **0.7.1** Python 2.6 compat fix
- **0.7.0** Reconnect broken server connections automatically (after first connect).
- **0.6.0** Various pull requests from other devs integrated. Thanks to @devrandom, @ysangkok!
- **0.5.3** Documents the build/release process (no functional changes).
- **0.5.2** Make aiosocks and bottom modules optional at runtime (thanks to @BioMike)
- **0.5.1** Minor bug fixes
- **0.5.0** First public release.


TODO List
=========

- be more robust about failed servers, reconnect and handle it.
- connect to a few (3?) servers and compare top block and response times; pick best
- some sort of persistant server list that can be updated as we run
- type checking of parameters sent to server (maybe)?
- lots of test code
- an example that finds servers that do SSL with self-signed certificate
- an example that fingerprints servers to learn what codebase they use
- some bitcoin-specific code that all clients would need; like block header to hash

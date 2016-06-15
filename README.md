
# Connectrum

## Stratum (electrum-server) Client Protocol library

Use python3 to be a client to the Electrum server network. It makes heavy use of
`asyncio` module and newer Python 3.5 keywords such as `await` and `async`.

This is meant to be a mostly-clean room implementation, but isn't.

For non-server applications, you can probably find all you need
already in the standard Electrum code and command line.


## Setup

    virtualenv -p python3 ENV
    (activate ENV)
    pip install -r requirements.txt


## References

https://github.com/python/asyncio/wiki/ThirdParty

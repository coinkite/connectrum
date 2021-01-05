import hashlib


# for compatibility with following code...
class SHA256:
    new = hashlib.sha256


if str != bytes:
    # Python 3.x
    def ord(c):
        return c


    def chr(n):
        return bytes((n,))

### BEGIN: Copied from https://bitcointalk.org/index.php?topic=1026.0 (public domain)
__b58chars = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
__b58base = len(__b58chars)


def b58encode(v):
    """ encode v, which is a string of bytes, to base58.
    """

    long_value = 0
    for (i, c) in enumerate(v[::-1]):
        long_value += (256 ** i) * ord(c)

    result = ''
    while long_value >= __b58base:
        div, mod = divmod(long_value, __b58base)
        result = __b58chars[mod] + result
        long_value = div
    result = __b58chars[long_value] + result

    # Bitcoin does a little leading-zero-compression:
    # leading 0-bytes in the input become leading-1s
    nPad = 0
    for c in v:
        if c == '\0':
            nPad += 1
        else:
            break

    return (__b58chars[0] * nPad) + result


def b58decode(v, length):
    """ decode v into a string of len bytes
    """
    long_value = 0
    for (i, c) in enumerate(v[::-1]):
        long_value += __b58chars.find(c) * (__b58base ** i)

    result = bytes()
    while long_value >= 256:
        div, mod = divmod(long_value, 256)
        result = chr(mod) + result
        long_value = div
    result = chr(long_value) + result

    nPad = 0
    for c in v:
        if c == __b58chars[0]:
            nPad += 1
        else:
            break

    result = chr(0) * nPad + result
    if length is not None and len(result) != length:
        return None

    return result


def get_bcaddress_version(strAddress):
    """ Returns None if strAddress is invalid.  Otherwise returns integer version of address. """
    addr = b58decode(strAddress, 25)
    if addr is None: return None
    version = addr[0]
    checksum = addr[-4:]
    vh160 = addr[
            :-4]  # Version plus hash160 is what is checksummed
    h3 = SHA256.new(SHA256.new(vh160).digest()).digest()
    if h3[0:4] == checksum:
        return ord(version)
    return None


###   END: Copied from https://bitcointalk.org/index.php?topic=1026.0 (public domain)

if __name__ == '__main__':
    # Test case
    assert get_bcaddress_version('15VjRaDX9zpbA8LVnbrCAFzrVzN7ixHNsC') == 0
    _ohai = 'o hai'.encode('ascii')
    _tmp = b58encode(_ohai)
    assert _tmp == 'DYB3oMS'
    assert b58decode(_tmp, 5) == _ohai
    print("Tests passed")

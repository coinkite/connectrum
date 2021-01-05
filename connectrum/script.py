from bitcoin_b58 import b58decode
from hashlib import sha256


def dblsha(b):
    return sha256(sha256(b).digest()).digest()


WitnessMagic = b'\xaa\x21\xa9\xed'


def _Address2PKH(addr):
    try:
        addr = b58decode(addr, 25)
    except:
        return None
    if addr is None:
        return None
    ver = addr[0]
    cksumA = addr[-4:]
    cksumB = dblsha(addr[:-4])[:4]
    if cksumA != cksumB:
        return None
    return (ver, addr[1:-4])


class BitcoinScript:
    @classmethod
    def toAddress(cls, addr):
        d = _Address2PKH(addr)
        if not d:
            raise ValueError('invalid address')
        (ver, pubkeyhash) = d
        if ver == 35 or ver == 111:
            return b'\x76\xa9\x14' + pubkeyhash + b'\x88\xac'
        elif ver == 5 or ver == 196:
            return b'\xa9\x14' + pubkeyhash + b'\x87'
        raise ValueError('invalid address version')

    @classmethod
    def commitment(cls, commitment):
        clen = len(commitment)
        if clen > 0x4b:
            raise NotImplementedError
        return b'\x6a' + bytes((clen,)) + commitment




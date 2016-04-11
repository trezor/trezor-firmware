from TrezorCrypto import Base58
from . import sha256

_base58 = Base58()

def encode(data):
    return _base58.encode(data)

def decode(string):
    return _base58.decode(string)

def encode_check(data, hashlen=4):
    h = sha256.hash(data)
    return encode(data + h[:hashlen])

def decode_check(string, hashlen=4):
    data = decode(string)
    d, h = data[:-hashlen], data[-hashlen:]
    if sha256.hash(d) != h:
        raise RuntimeError('Checksum error')
    return d

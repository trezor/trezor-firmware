from TrezorCrypto import Base58
from .hashlib import sha256

_base58 = Base58()

def encode(data):
    return _base58.encode(data)

def decode(string):
    return _base58.decode(string)

def encode_check(data, hashlen=4):
    h = sha256(sha256(data).digest()).digest()
    return encode(data + h[:hashlen])

def decode_check(string, hashlen=4):
    data = decode(string)
    d, h1 = data[:-hashlen], data[-hashlen:]
    h2 = sha256(sha256(d).digest).digest()[:4]
    if h1 != h2:
        raise RuntimeError('Checksum error')
    return d

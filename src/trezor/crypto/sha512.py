from TrezorCrypto import Sha512

_sha512 = Sha512()

def hash(data):
    return _sha512.hash(data)

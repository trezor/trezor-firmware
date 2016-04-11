from TrezorCrypto import Sha256

_sha256 = Sha256()

def hash(data):
    return _sha256.hash(data)

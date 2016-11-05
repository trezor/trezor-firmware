from TrezorCrypto import Blake2s as blake2s
from TrezorCrypto import Ripemd160 as ripemd160
from TrezorCrypto import Sha1 as sha1
from TrezorCrypto import Sha256 as sha256
from TrezorCrypto import Sha512 as sha512
from TrezorCrypto import Sha3_256 as sha3_256
from TrezorCrypto import Sha3_512 as sha3_512

class HashIO:

    def __init__(self, hashfunc=sha256):
        self.hashfunc = hashfunc
        self.ctx = hashfunc()

    def write(self, data):
        self.ctx.update(data)

    def getvalue(self):
        return self.ctx.digest()

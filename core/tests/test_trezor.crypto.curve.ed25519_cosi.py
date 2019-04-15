from common import *

from trezor.crypto import random
from trezor.crypto.curve import ed25519


class TestCryptoEd25519Cosi(unittest.TestCase):

    def test_cosi(self):

        for N in range(1, 11):

            # generate random message to be signed
            msg = random.bytes(128)

            # phase 0: create priv/pubkeys and combine pubkeys
            keys = [None] * N
            pubkeys = [None] * N
            for j in range(N):
                keys[j] = ed25519.generate_secret()
                pubkeys[j] = ed25519.publickey(keys[j])

            pubkey = ed25519.cosi_combine_publickeys(pubkeys)

            # phase 1: create nonces, commitments (R values) and combine commitments
            nonces = [None] * N
            Rs = [None] * N
            for j in range(N):
                nonces[j] = ed25519.generate_secret()
                Rs[j] = ed25519.publickey(nonces[j])

            R = ed25519.cosi_combine_publickeys(Rs)

            # phase 2: sign and combine signatures
            sigs = [None] * N
            for j in range(N):
                sigs[j] = ed25519.cosi_sign(keys[j], msg, nonces[j], R, pubkey)

            sig = ed25519.cosi_combine_signatures(R, sigs)

            # check signature using normal ed25519.verify
            res = ed25519.verify(pubkey, sig, msg)
            self.assertTrue(res)


if __name__ == '__main__':
    unittest.main()

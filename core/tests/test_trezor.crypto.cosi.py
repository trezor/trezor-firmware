# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.crypto import cosi, random
from trezor.crypto.curve import ed25519


class TestCryptoEd25519Cosi(unittest.TestCase):
    def random_signers(self, N: int) -> tuple[list[bytes], list[bytes]]:
        keys = []
        pubkeys = []
        for j in range(N):
            keys.append(ed25519.generate_secret())
            pubkeys.append(ed25519.publickey(keys[j]))
        return keys, pubkeys

    def cosign(
        self, message: bytes, keys: list[bytes], pubkeys: list[bytes]
    ) -> tuple[bytes, bytes]:
        # phase 0: combine pubkeys
        pubkey = cosi.combine_publickeys(pubkeys)

        # phase 1: create nonces, commitments (R values) and combine commitments
        nonces = []
        Rs = []
        for _ in range(len(keys)):
            nonce, R = cosi.commit()
            nonces.append(nonce)
            Rs.append(R)

        R = ed25519.cosi_combine_publickeys(Rs)

        # phase 2: sign and combine signatures
        sigs = []
        for key, nonce in zip(keys, nonces):
            sigs.append(cosi.sign(key, message, nonce, R, pubkey))

        return pubkey, cosi.combine_signatures(R, sigs)

    def test_cosi(self):
        for N in range(1, 11):
            # generate random inputs
            msg = random.bytes(128)
            keys, pubkeys = self.random_signers(N)

            # generate combined signature
            pubkey, sig = self.cosign(msg, keys, pubkeys)

            # check signature using normal ed25519.verify
            res = ed25519.verify(pubkey, sig, msg)
            self.assertTrue(res)

    def test_select_keys(self):
        keys, pubkeys = self.random_signers(5)
        # try all possible combinations of signers = all 5-bit sigmasks
        for sigmask in range(1, 32):
            selected_keys = cosi.select_keys(sigmask, keys)
            selected_pubkeys = cosi.select_keys(sigmask, pubkeys)

            # check that the selection picks the right key combinations
            for key, pubkey in zip(selected_keys, selected_pubkeys):
                self.assertEqual(ed25519.publickey(key), pubkey)

            # count number of ones
            count = 0
            for i in range(5):
                if sigmask & (1 << i):
                    count += 1
            self.assertEqual(len(selected_keys), count)
            self.assertEqual(len(selected_pubkeys), count)

    def test_verify(self):
        keys, all_pubkeys = self.random_signers(5)
        # try all possible combinations of signers = all 5-bit sigmasks
        for sigmask in range(1, 32):
            message = random.bytes(128)

            selected_keys = cosi.select_keys(sigmask, keys)
            selected_pubkeys = cosi.select_keys(sigmask, all_pubkeys)

            _, sig = self.cosign(message, selected_keys, selected_pubkeys)

            res = cosi.verify(sig, message, len(selected_keys), all_pubkeys, sigmask)
            self.assertTrue(res)

            res = cosi.verify(sig, message, 1, all_pubkeys, sigmask)
            self.assertTrue(res)

            res = cosi.verify(
                sig, message, len(selected_keys) + 1, all_pubkeys, sigmask
            )
            self.assertFalse(res)


if __name__ == "__main__":
    unittest.main()

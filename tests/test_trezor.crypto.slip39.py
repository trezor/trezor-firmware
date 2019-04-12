from common import *

from trezor.crypto import slip39
from slip39_vectors import vectors
from trezorcrypto import shamir


class TestCryptoSlip39(unittest.TestCase):

    def test_shamir(self):
        shamir_mnemonic = slip39.ShamirMnemonic()
        for mnemonics, secret in vectors:
            if secret:
                self.assertEqual(shamir_mnemonic.combine_mnemonics(mnemonics, b"TREZOR"), unhexlify(secret))
            else:
                with self.assertRaises(slip39.MnemonicError):
                    shamir_mnemonic.combine_mnemonics(mnemonics, b"TREZOR")


if __name__ == '__main__':
    unittest.main()

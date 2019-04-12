from common import *

from trezor.crypto import slip39
from slip39_vectors import vectors


class TestCryptoSlip39(unittest.TestCase):
    MS = b"ABCDEFGHIJKLMNOP"
    shamir = slip39.ShamirMnemonic()


    def test_basic_sharing_random(self):
        mnemonics = self.shamir.generate_mnemonics_random(1, [(3, 5)])[0]
        self.assertEqual(self.shamir.combine_mnemonics(mnemonics[1:4]), self.shamir.combine_mnemonics(mnemonics))


    def test_basic_sharing_fixed(self):
        mnemonics = self.shamir.generate_mnemonics(1, [(3, 5)], self.MS)[0]
        self.assertEqual(self.shamir.combine_mnemonics(mnemonics), self.MS)
        self.assertEqual(self.shamir.combine_mnemonics(mnemonics[1:4]), self.MS)
        with self.assertRaises(slip39.MnemonicError):
            self.shamir.combine_mnemonics(mnemonics[1:3])


    def test_passphrase(self):
        mnemonics = self.shamir.generate_mnemonics(1, [(3, 5)], self.MS, b"TREZOR")[0]
        self.assertEqual(self.shamir.combine_mnemonics(mnemonics[1:4], b"TREZOR"), self.MS)
        self.assertNotEqual(self.shamir.combine_mnemonics(mnemonics[1:4]), self.MS)


    def test_iteration_exponent(self):
        mnemonics = self.shamir.generate_mnemonics(1, [(3, 5)], self.MS, b"TREZOR", 1)[0]
        self.assertEqual(self.shamir.combine_mnemonics(mnemonics[1:4], b"TREZOR"), self.MS)
        self.assertNotEqual(self.shamir.combine_mnemonics(mnemonics[1:4]), self.MS)

        mnemonics = self.shamir.generate_mnemonics(1, [(3, 5)], self.MS, b"TREZOR", 2)[0]
        self.assertEqual(self.shamir.combine_mnemonics(mnemonics[1:4], b"TREZOR"), self.MS)
        self.assertNotEqual(self.shamir.combine_mnemonics(mnemonics[1:4]), self.MS)


    def test_group_sharing(self):
        mnemonics = self.shamir.generate_mnemonics(2, [(3, 5), (2, 3), (2, 5), (1, 1)], self.MS)

        # All mnemonics.
        self.assertEqual(self.shamir.combine_mnemonics([mnemonic for group in mnemonics for mnemonic in group]), self.MS)

        # Minimal sets of mnemonics.
        self.assertEqual(self.shamir.combine_mnemonics([mnemonics[2][0], mnemonics[2][2], mnemonics[3][0]]), self.MS)
        self.assertEqual(self.shamir.combine_mnemonics([mnemonics[2][3], mnemonics[3][0], mnemonics[2][4]]), self.MS)

        # Two complete groups and one incomplete group.
        self.assertEqual(self.shamir.combine_mnemonics(mnemonics[0] + [mnemonics[1][1]] + mnemonics[2]), self.MS)
        self.assertEqual(self.shamir.combine_mnemonics(mnemonics[0][1:4] + mnemonics[1][1:3] + mnemonics[2][2:4]), self.MS)

        # One complete group and one incomplete group out of two groups required.
        with self.assertRaises(slip39.MnemonicError):
            self.shamir.combine_mnemonics(mnemonics[0][2:] + [mnemonics[1][0]])

        # One group of two required.
        with self.assertRaises(slip39.MnemonicError):
            self.shamir.combine_mnemonics(mnemonics[0][1:4])


    def test_vectors(self):
        for mnemonics, secret in vectors:
            if secret:
                self.assertEqual(self.shamir.combine_mnemonics(mnemonics, b"TREZOR"), unhexlify(secret))
            else:
                with self.assertRaises(slip39.MnemonicError):
                    self.shamir.combine_mnemonics(mnemonics, b"TREZOR")


    def test_invalid_rs1024_checksum(self):
        mnemonics = [
            "artist away academic academic dismiss spill unkind pencil lair sugar usher elegant paces sweater firm gravity deal body chest sugar"
        ]
        with self.assertRaises(slip39.MnemonicError):
            self.shamir.combine_mnemonics(mnemonics)


if __name__ == '__main__':
    unittest.main()

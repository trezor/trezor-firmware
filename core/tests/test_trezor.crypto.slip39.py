from common import *

from trezor.crypto import slip39
from slip39_vectors import vectors


class TestCryptoSlip39(unittest.TestCase):
    MS = b"ABCDEFGHIJKLMNOP"

    def test_basic_sharing_random(self):
        mnemonics = slip39.generate_mnemonics_random(1, [(3, 5)])[0]
        self.assertEqual(slip39.combine_mnemonics(mnemonics[1:4]), slip39.combine_mnemonics(mnemonics))


    def test_basic_sharing_fixed(self):
        mnemonics = slip39.generate_mnemonics(1, [(3, 5)], self.MS)[0]
        identifier, exponent, ems = slip39.combine_mnemonics(mnemonics)
        self.assertEqual(slip39.decrypt(identifier, exponent, ems, b""), self.MS)
        self.assertEqual(slip39.combine_mnemonics(mnemonics[1:4])[2], ems)
        with self.assertRaises(slip39.MnemonicError):
            slip39.combine_mnemonics(mnemonics[1:3])


    def test_passphrase(self):
        mnemonics = slip39.generate_mnemonics(1, [(3, 5)], self.MS, b"TREZOR")[0]
        identifier, exponent, ems = slip39.combine_mnemonics(mnemonics[1:4])
        self.assertEqual(slip39.decrypt(identifier, exponent, ems, b"TREZOR"), self.MS)
        self.assertNotEqual(slip39.decrypt(identifier, exponent, ems, b""), self.MS)


    def test_iteration_exponent(self):
        mnemonics = slip39.generate_mnemonics(1, [(3, 5)], self.MS, b"TREZOR", 1)[0]
        identifier, exponent, ems = slip39.combine_mnemonics(mnemonics[1:4])
        self.assertEqual(slip39.decrypt(identifier, exponent, ems, b"TREZOR"), self.MS)
        self.assertNotEqual(slip39.decrypt(identifier, exponent, ems, b""), self.MS)

        mnemonics = slip39.generate_mnemonics(1, [(3, 5)], self.MS, b"TREZOR", 2)[0]
        identifier, exponent, ems = slip39.combine_mnemonics(mnemonics[1:4])
        self.assertEqual(slip39.decrypt(identifier, exponent, ems, b"TREZOR"), self.MS)
        self.assertNotEqual(slip39.decrypt(identifier, exponent, ems, b""), self.MS)


    def test_group_sharing(self):
        mnemonics = slip39.generate_mnemonics(2, [(3, 5), (2, 3), (2, 5), (1, 1)], self.MS)

        # All mnemonics.
        identifier, exponent, ems = slip39.combine_mnemonics([mnemonic for group in mnemonics for mnemonic in group])
        self.assertEqual(slip39.decrypt(identifier, exponent, ems, b""), self.MS)

        # Minimal sets of mnemonics.
        self.assertEqual(slip39.combine_mnemonics([mnemonics[2][0], mnemonics[2][2], mnemonics[3][0]])[2], ems)
        self.assertEqual(slip39.combine_mnemonics([mnemonics[2][3], mnemonics[3][0], mnemonics[2][4]])[2], ems)

        # Two complete groups and one incomplete group.
        self.assertEqual(slip39.combine_mnemonics(mnemonics[0] + [mnemonics[1][1]] + mnemonics[2])[2], ems)
        self.assertEqual(slip39.combine_mnemonics(mnemonics[0][1:4] + mnemonics[1][1:3] + mnemonics[2][2:4])[2], ems)

        # One complete group and one incomplete group out of two groups required.
        with self.assertRaises(slip39.MnemonicError):
            slip39.combine_mnemonics(mnemonics[0][2:] + [mnemonics[1][0]])

        # One group of two required.
        with self.assertRaises(slip39.MnemonicError):
            slip39.combine_mnemonics(mnemonics[0][1:4])


    def test_invalid_sharing(self):
        # Short master secret.
        with self.assertRaises(ValueError):
            slip39.generate_mnemonics(1, [(2, 3)], self.MS[:14])

        # Odd length master secret.
        with self.assertRaises(ValueError):
            slip39.generate_mnemonics(1, [(2, 3)], self.MS + b"X")

        # Group threshold exceeds number of groups.
        with self.assertRaises(ValueError):
            slip39.generate_mnemonics(3, [(3, 5), (2, 5)], self.MS)

        # Group with multiple members and threshold 1.
        with self.assertRaises(ValueError):
            slip39.generate_mnemonics(2, [(3, 5), (1, 3), (2, 5)], self.MS)


    def test_vectors(self):
        for mnemonics, secret in vectors:
            if secret:
                identifier, exponent, ems = slip39.combine_mnemonics(mnemonics)
                self.assertEqual(slip39.decrypt(identifier, exponent, ems, b"TREZOR"), unhexlify(secret))
            else:
                with self.assertRaises(slip39.MnemonicError):
                    slip39.combine_mnemonics(mnemonics)


if __name__ == '__main__':
    unittest.main()

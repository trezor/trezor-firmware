from common import *
from trezor.crypto import slip39, random
from slip39_vectors import vectors

def combinations(iterable, r):
    # Taken from https://docs.python.org/3.7/library/itertools.html#itertools.combinations
    pool = tuple(iterable)
    n = len(pool)
    if r > n:
        return
    indices = list(range(r))
    yield tuple(pool[i] for i in indices)
    while True:
        for i in reversed(range(r)):
            if indices[i] != i + n - r:
                break
        else:
            return
        indices[i] += 1
        for j in range(i+1, r):
            indices[j] = indices[j-1] + 1
        yield tuple(pool[i] for i in indices)

class TestCryptoSlip39(unittest.TestCase):
    MS = b"ABCDEFGHIJKLMNOP"

    def test_basic_sharing_random(self):
        mnemonics = slip39.generate_mnemonics_random(1, [(3, 5)])[0]
        self.assertEqual(slip39.combine_mnemonics(mnemonics[:3]), slip39.combine_mnemonics(mnemonics[2:]))


    def test_basic_sharing_fixed(self):
        mnemonics = slip39.generate_mnemonics(1, [(3, 5)], self.MS)[0]
        identifier, exponent, ems = slip39.combine_mnemonics(mnemonics[:3])
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
        group_threshold = 2
        group_sizes = (5, 3, 5, 1)
        member_thresholds = (3, 2, 2, 1)
        mnemonics = slip39.generate_mnemonics(
            group_threshold, list(zip(member_thresholds, group_sizes)), self.MS
        )

        # Test all valid combinations of mnemonics.
        for groups in combinations(zip(mnemonics, member_thresholds), group_threshold):
            for group1_subset in combinations(groups[0][0], groups[0][1]):
                for group2_subset in combinations(groups[1][0], groups[1][1]):
                    mnemonic_subset = list(group1_subset + group2_subset)
                    random.shuffle(mnemonic_subset)
                    identifier, exponent, ems = slip39.combine_mnemonics(mnemonic_subset)
                    self.assertEqual(slip39.decrypt(identifier, exponent, ems, b""), self.MS)


        # Minimal sets of mnemonics.
        identifier, exponent, ems = slip39.combine_mnemonics([mnemonics[2][0], mnemonics[2][2], mnemonics[3][0]])
        self.assertEqual(slip39.decrypt(identifier, exponent, ems, b""), self.MS)
        self.assertEqual(slip39.combine_mnemonics([mnemonics[2][3], mnemonics[3][0], mnemonics[2][4]])[2], ems)

        # One complete group and one incomplete group out of two groups required.
        with self.assertRaises(slip39.MnemonicError):
            slip39.combine_mnemonics(mnemonics[0][2:] + [mnemonics[1][0]])

        # One group of two required.
        with self.assertRaises(slip39.MnemonicError):
            slip39.combine_mnemonics(mnemonics[0][1:4])


    def test_group_sharing_threshold_1(self):
        group_threshold = 1
        group_sizes = (5, 3, 5, 1)
        member_thresholds = (3, 2, 2, 1)
        mnemonics = slip39.generate_mnemonics(
            group_threshold, list(zip(member_thresholds, group_sizes)), self.MS
        )

        # Test all valid combinations of mnemonics.
        for group, threshold in zip(mnemonics, member_thresholds):
            for group_subset in combinations(group, threshold):
                mnemonic_subset = list(group_subset)
                random.shuffle(mnemonic_subset)
                identifier, exponent, ems = slip39.combine_mnemonics(mnemonic_subset)
                self.assertEqual(slip39.decrypt(identifier, exponent, ems, b""), self.MS)


    def test_all_groups_exist(self):
        for group_threshold in (1, 2, 5):
            mnemonics = slip39.generate_mnemonics(
                group_threshold, [(3, 5), (1, 1), (2, 3), (2, 5), (3, 5)], self.MS
            )
            self.assertEqual(len(mnemonics), 5)
            self.assertEqual(len(sum(mnemonics, [])), 19)

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

        # Invalid group threshold.
        with self.assertRaises(ValueError):
            slip39.generate_mnemonics(0, [(3, 5), (2, 5)], self.MS)

        # Member threshold exceeds number of members.
        with self.assertRaises(ValueError):
            slip39.generate_mnemonics(2, [(3, 2), (2, 5)], self.MS)

        # Invalid member threshold.
        with self.assertRaises(ValueError):
            slip39.generate_mnemonics(2, [(0, 2), (2, 5)], self.MS)

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

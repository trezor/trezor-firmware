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
    EMS = b"ABCDEFGHIJKLMNOP"

    def test_basic_sharing_random(self):
        ems = random.bytes(32)
        identifier = slip39.generate_random_identifier()
        mnemonics = slip39.split_ems(1, [(3, 5)], identifier, 1, ems)
        mnemonics = mnemonics[0]
        self.assertEqual(slip39.recover_ems(mnemonics[:3]), slip39.recover_ems(mnemonics[2:]))


    def test_basic_sharing_fixed(self):
        generated_identifier = slip39.generate_random_identifier()
        mnemonics = slip39.split_ems(1, [(3, 5)], generated_identifier, 1, self.EMS)
        mnemonics = mnemonics[0]
        identifier, exponent, ems = slip39.recover_ems(mnemonics[:3])
        self.assertEqual(ems, self.EMS)
        self.assertEqual(generated_identifier, identifier)
        self.assertEqual(slip39.recover_ems(mnemonics[1:4])[2], ems)
        with self.assertRaises(slip39.MnemonicError):
            slip39.recover_ems(mnemonics[1:3])


    def test_iteration_exponent(self):
        identifier = slip39.generate_random_identifier()
        mnemonics = slip39.split_ems(1, [(3, 5)], identifier, 1, self.EMS)
        mnemonics = mnemonics[0]
        identifier, exponent, ems  = slip39.recover_ems(mnemonics[1:4])
        self.assertEqual(ems, self.EMS)

        identifier = slip39.generate_random_identifier()
        mnemonics = slip39.split_ems(1, [(3, 5)], identifier, 2, self.EMS)
        mnemonics = mnemonics[0]
        identifier, exponent, ems = slip39.recover_ems(mnemonics[1:4])
        self.assertEqual(ems, self.EMS)


    def test_group_sharing(self):
        group_threshold = 2
        group_sizes = (5, 3, 5, 1)
        member_thresholds = (3, 2, 2, 1)
        identifier = slip39.generate_random_identifier()
        mnemonics = slip39.split_ems(
            group_threshold, list(zip(member_thresholds, group_sizes)), identifier, 1, self.EMS
        )

        # Test all valid combinations of mnemonics.
        for groups in combinations(zip(mnemonics, member_thresholds), group_threshold):
            for group1_subset in combinations(groups[0][0], groups[0][1]):
                for group2_subset in combinations(groups[1][0], groups[1][1]):
                    mnemonic_subset = list(group1_subset + group2_subset)
                    random.shuffle(mnemonic_subset)
                    identifier, exponent, ems = slip39.recover_ems(mnemonic_subset)
                    self.assertEqual(ems, self.EMS)


        # Minimal sets of mnemonics.
        identifier, exponent, ems = slip39.recover_ems([mnemonics[2][0], mnemonics[2][2], mnemonics[3][0]])
        self.assertEqual(ems, self.EMS)
        self.assertEqual(slip39.recover_ems([mnemonics[2][3], mnemonics[3][0], mnemonics[2][4]])[2], ems)

        # One complete group and one incomplete group out of two groups required.
        with self.assertRaises(slip39.MnemonicError):
            slip39.recover_ems(mnemonics[0][2:] + [mnemonics[1][0]])

        # One group of two required.
        with self.assertRaises(slip39.MnemonicError):
            slip39.recover_ems(mnemonics[0][1:4])


    def test_group_sharing_threshold_1(self):
        group_threshold = 1
        group_sizes = (5, 3, 5, 1)
        member_thresholds = (3, 2, 2, 1)
        identifier = slip39.generate_random_identifier()
        mnemonics = slip39.split_ems(
            group_threshold, list(zip(member_thresholds, group_sizes)), identifier, 1, self.EMS
        )

        # Test all valid combinations of mnemonics.
        for group, threshold in zip(mnemonics, member_thresholds):
            for group_subset in combinations(group, threshold):
                mnemonic_subset = list(group_subset)
                random.shuffle(mnemonic_subset)
                identifier, exponent, ems = slip39.recover_ems(mnemonic_subset)
                self.assertEqual(ems, self.EMS)


    def test_all_groups_exist(self):
        for group_threshold in (1, 2, 5):
            identifier = slip39.generate_random_identifier()
            mnemonics = slip39.split_ems(
                group_threshold, [(3, 5), (1, 1), (2, 3), (2, 5), (3, 5)], identifier, 1, self.EMS
            )
            self.assertEqual(len(mnemonics), 5)
            self.assertEqual(len(sum(mnemonics, [])), 19)


    def test_invalid_sharing(self):
        identifier = slip39.generate_random_identifier()

        # Group threshold exceeds number of groups.
        with self.assertRaises(ValueError):
            slip39.split_ems(3, [(3, 5), (2, 5)], identifier, 1, self.EMS)

        # Invalid group threshold.
        with self.assertRaises(ValueError):
            slip39.split_ems(0, [(3, 5), (2, 5)], identifier, 1, self.EMS)

        # Member threshold exceeds number of members.
        with self.assertRaises(ValueError):
            slip39.split_ems(2, [(3, 2), (2, 5)], identifier, 1, self.EMS)

        # Invalid member threshold.
        with self.assertRaises(ValueError):
            slip39.split_ems(2, [(0, 2), (2, 5)], identifier, 1, self.EMS)

        # Group with multiple members and threshold 1.
        with self.assertRaises(ValueError):
            slip39.split_ems(2, [(3, 5), (1, 3), (2, 5)], identifier, 1, self.EMS)


    def test_vectors(self):
        for mnemonics, secret in vectors:
            if secret:
                identifier, exponent, ems = slip39.recover_ems(mnemonics)
                self.assertEqual(slip39.decrypt(ems, b"TREZOR", exponent, identifier), unhexlify(secret))
            else:
                with self.assertRaises(slip39.MnemonicError):
                    slip39.recover_ems(mnemonics)


    def test_error_location(self):
        mnemonics = [
            "duckling enlarge academic academic agency result length solution fridge kidney coal piece deal husband erode duke ajar critical decision keyboard",
            "theory painting academic academic armed sweater year military elder discuss acne wildlife boring employer fused large satoshi bundle carbon diagnose anatomy hamster leaves tracks paces beyond phantom capital marvel lips brave detect luck",
        ]
        for mnemonic in mnemonics:
            data = tuple(slip39._mnemonic_to_indices(mnemonic))
            self.assertEqual(slip39._rs1024_error_index(data), None)
            for i in range(len(data)):
                for _ in range(50):
                    error_data = error_data = data[:i] + (data[i] ^ (random.uniform(1023) + 1), ) + data[i + 1:]
                    self.assertEqual(slip39._rs1024_error_index(error_data), i)


if __name__ == '__main__':
    unittest.main()

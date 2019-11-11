from common import *
from mock_storage import mock_storage

import storage
import storage.recovery
from apps.management.recovery_device.recover import process_slip39

MNEMONIC_SLIP39_BASIC_20_3of6 = [
    "extra extend academic bishop cricket bundle tofu goat apart victim enlarge program behavior permit course armed jerky faint language modern",
    "extra extend academic acne away best indicate impact square oasis prospect painting voting guest either argue username racism enemy eclipse",
    "extra extend academic arcade born dive legal hush gross briefing talent drug much home firefly toxic analysis idea umbrella slice",
]
# Shamir shares (128 bits, 2 groups from 1 of 1, 1 of 1, 3 of 5, 2 of 6)
MNEMONIC_SLIP39_ADVANCED_20 = [
    "eraser senior beard romp adorn nuclear spill corner cradle style ancient family general leader ambition exchange unusual garlic promise voice",
    "eraser senior ceramic snake clay various huge numb argue hesitate auction category timber browser greatest hanger petition script leaf pickup",
    "eraser senior ceramic shaft dynamic become junior wrist silver peasant force math alto coal amazing segment yelp velvet image paces",
    "eraser senior ceramic round column hawk trust auction smug shame alive greatest sheriff living perfect corner chest sled fumes adequate",
]
# Shamir shares (256 bits, 2 groups from 1 of 1, 1 of 1, 3 of 5, 2 of 6):
MNEMONIC_SLIP39_ADVANCED_33 = [
    "wildlife deal beard romp alcohol space mild usual clothes union nuclear testify course research heat listen task location thank hospital slice smell failure fawn helpful priest ambition average recover lecture process dough stadium",
    "wildlife deal acrobat romp anxiety axis starting require metric flexible geology game drove editor edge screw helpful have huge holy making pitch unknown carve holiday numb glasses survive already tenant adapt goat fangs",
]


class TestSlip39(unittest.TestCase):

    @mock_storage
    def test_process_slip39_basic(self):
        storage.recovery.set_in_progress(True)

        # first share (member index 5)
        first = MNEMONIC_SLIP39_BASIC_20_3of6[0]
        secret, share = process_slip39(first)
        self.assertIsNone(secret)
        self.assertEqual(share.group_count, storage.recovery.get_slip39_group_count())
        self.assertEqual(share.iteration_exponent, storage.recovery.get_slip39_iteration_exponent())
        self.assertEqual(share.identifier, storage.recovery.get_slip39_identifier())
        self.assertEqual(storage.recovery.get_slip39_remaining_shares(0), 2)
        self.assertEqual(storage.recovery_shares.get(share.index, share.group_index), first)

        # second share (member index 0)
        second = MNEMONIC_SLIP39_BASIC_20_3of6[1]
        secret, share = process_slip39(second)
        self.assertIsNone(secret)
        self.assertEqual(storage.recovery.get_slip39_remaining_shares(0), 1)
        self.assertEqual(storage.recovery_shares.get(share.index, share.group_index), second)
        self.assertEqual(storage.recovery_shares.fetch_group(share.group_index), [second, first])  # ordered by index

        # third share (member index 3)
        third = MNEMONIC_SLIP39_BASIC_20_3of6[2]
        secret, share = process_slip39(third)
        self.assertEqual(secret, b'I\x1by[\x80\xfc!\xcc\xdfFl\x0f\xbc\x98\xc8\xfc')
        self.assertEqual(storage.recovery.get_slip39_remaining_shares(0), 0)
        self.assertEqual(storage.recovery_shares.get(share.index, share.group_index), third)
        self.assertEqual(storage.recovery_shares.fetch_group(share.group_index), [second, third, first])  # ordered by index

    @mock_storage
    def test_process_slip39_advanced(self):
        storage.recovery.set_in_progress(True)

        # complete group 1 (1of1)
        words = MNEMONIC_SLIP39_ADVANCED_20[0]
        secret, share = process_slip39(words)
        self.assertIsNone(secret)
        self.assertEqual(share.group_count, storage.recovery.get_slip39_group_count())
        self.assertEqual(share.iteration_exponent, storage.recovery.get_slip39_iteration_exponent())
        self.assertEqual(share.identifier, storage.recovery.get_slip39_identifier())
        self.assertEqual(storage.recovery.fetch_slip39_remaining_shares(), [16, 0, 16, 16])
        self.assertEqual(storage.recovery_shares.get(share.index, share.group_index), words)

        # member index 4 from group 2 (3of5)
        words = MNEMONIC_SLIP39_ADVANCED_20[1]
        secret, share = process_slip39(words)
        self.assertIsNone(secret)
        self.assertEqual(share.group_count, storage.recovery.get_slip39_group_count())
        self.assertEqual(share.iteration_exponent, storage.recovery.get_slip39_iteration_exponent())
        self.assertEqual(share.identifier, storage.recovery.get_slip39_identifier())
        self.assertEqual(storage.recovery_shares.get(share.index, share.group_index), words)
        self.assertEqual(storage.recovery_shares.fetch_group(1), [MNEMONIC_SLIP39_ADVANCED_20[0]])
        self.assertEqual(storage.recovery_shares.fetch_group(2), [MNEMONIC_SLIP39_ADVANCED_20[1]])
        self.assertEqual(storage.recovery.fetch_slip39_remaining_shares(), [16, 0, 2, 16])

        # member index 2 from group 2
        words = MNEMONIC_SLIP39_ADVANCED_20[2]
        secret, share = process_slip39(words)
        self.assertIsNone(secret)
        self.assertEqual(share.group_count, storage.recovery.get_slip39_group_count())
        self.assertEqual(share.iteration_exponent, storage.recovery.get_slip39_iteration_exponent())
        self.assertEqual(share.identifier, storage.recovery.get_slip39_identifier())
        self.assertEqual(storage.recovery_shares.get(share.index, share.group_index), words)
        self.assertEqual(storage.recovery_shares.fetch_group(1), [MNEMONIC_SLIP39_ADVANCED_20[0]])
        self.assertEqual(storage.recovery_shares.fetch_group(2), [MNEMONIC_SLIP39_ADVANCED_20[2], MNEMONIC_SLIP39_ADVANCED_20[1]])
        self.assertEqual(storage.recovery.fetch_slip39_remaining_shares(), [16, 0, 1, 16])

        # last member index 0 from group 2
        # now group 2 is complete => the whole Shamir recovery is completed
        words = MNEMONIC_SLIP39_ADVANCED_20[3]
        secret, share = process_slip39(words)
        self.assertEqual(secret, b'\xc2\xd2\xe2j\xd0`#\xc6\x01E\xf1P\xab\xe2\xdd+')
        self.assertEqual(share.group_count, storage.recovery.get_slip39_group_count())
        self.assertEqual(share.iteration_exponent, storage.recovery.get_slip39_iteration_exponent())
        self.assertEqual(share.identifier, storage.recovery.get_slip39_identifier())
        self.assertEqual(storage.recovery_shares.get(share.index, share.group_index), words)
        self.assertEqual(storage.recovery_shares.fetch_group(1), [MNEMONIC_SLIP39_ADVANCED_20[0]])
        self.assertEqual(storage.recovery_shares.fetch_group(2), [MNEMONIC_SLIP39_ADVANCED_20[3], MNEMONIC_SLIP39_ADVANCED_20[2], MNEMONIC_SLIP39_ADVANCED_20[1]])
        self.assertEqual(storage.recovery.fetch_slip39_remaining_shares(), [16, 0, 0, 16])

    @mock_storage
    def test_exceptions(self):
        storage.recovery.set_in_progress(True)

        words = MNEMONIC_SLIP39_BASIC_20_3of6[0]
        secret, share = process_slip39(words)
        self.assertIsNone(secret)

        # same mnemonic
        words = MNEMONIC_SLIP39_BASIC_20_3of6[0]
        with self.assertRaises(RuntimeError):
            secret, share = process_slip39(words)
            self.assertIsNone(secret)

        # identifier mismatch
        words = MNEMONIC_SLIP39_ADVANCED_20[0]
        with self.assertRaises(RuntimeError):
            secret, share = process_slip39(words)
            self.assertIsNone(secret)

        # same identifier but different group settings
        words = MNEMONIC_SLIP39_BASIC_20_3of6[0]
        w = words.split()
        w[2] = "check"  # change the group settings
        w[3] = "mortgage"
        w[17] = "garden"  # modify checksum accordingly
        w[18] = "merchant"
        w[19] = "merchant"
        words = " ".join(w)
        with self.assertRaises(RuntimeError):
            secret, share = process_slip39(words)
            self.assertIsNone(secret)


if __name__ == "__main__":
    unittest.main()

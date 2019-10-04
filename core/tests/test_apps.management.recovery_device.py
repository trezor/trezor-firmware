from common import *
from storage import mock_storage

import apps.common.storage.recovery
from apps.common import storage
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
    def test_process_slip39(self):
        storage.recovery.set_in_progress(True)
        words = MNEMONIC_SLIP39_BASIC_20_3of6[0]
        secret, share = process_slip39(words)
        self.assertIsNone(secret)
        self.assertEqual(share.group_count, storage.recovery.get_slip39_group_count())


if __name__ == "__main__":
    unittest.main()

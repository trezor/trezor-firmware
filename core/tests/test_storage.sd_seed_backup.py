from common import *

from trezorio import sdcard, fatfs
from storage.sd_seed_backup import *


class TestStorageSdSeedBackup(unittest.TestCase):
    # TODO add more tests, also with partly damaged backup

    def setUp(self):
        self.mnemonic = (
            "crane mesh that gain predict open dice defy lottery toddler coin upgrade"
        )

    def test_backup_and_restore(self):
        # with self.assertRaises(fatfs.FatFSError):
        #     store_seed_on_sdcard(self.mnemonic.encode("utf-8"))

        sdcard.power_on()
        fatfs.mkfs(True)
        success = store_seed_on_sdcard(self.mnemonic.encode("utf-8"))
        self.assertTrue(success)

        restored = recover_seed_from_sdcard()
        self.assertEqual(self.mnemonic, restored)


if __name__ == "__main__":
    unittest.main()

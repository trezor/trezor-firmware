from common import *

from storage.sd_seed_backup import *
from trezor import io, sdcard


class TestStorageSdSeedBackup(unittest.TestCase):
    # TODO add more tests, also for repairing the backup card

    def setUp(self):
        self.mnemonic = (
            "crane mesh that gain predict open dice defy lottery toddler coin upgrade"
        )

    def test_backup_and_restore(self):
        # with self.assertRaises(fatfs.FatFSError):
        #     store_seed_on_sdcard(self.mnemonic.encode("utf-8"))

        io.sdcard.power_on()
        io.fatfs.mkfs(True)
        io.fatfs.mount()

        success = store_seed_on_sdcard(self.mnemonic.encode("utf-8"))
        self.assertTrue(success)

        restored = recover_seed_from_sdcard()
        self.assertEqual(self.mnemonic, restored)

        io.fatfs.unmount()
        io.sdcard.power_off()

    def test_backup_partlywipe_restore(self):
        with sdcard.filesystem(mounted=True):
            success = store_seed_on_sdcard(self.mnemonic.encode("utf-8"))
            self.assertTrue(success)

        # wipe half of the card, restore must succeed
        block_buffer = bytearray(SDCARD_BLOCK_SIZE_B)
        with sdcard.filesystem(mounted=False):
            for block_num in range((io.sdcard.capacity() // 2) // io.sdcard.BLOCK_SIZE):
                io.sdcard.write(block_num, block_buffer)

        with sdcard.filesystem(mounted=False):
            restored = recover_seed_from_sdcard()
            self.assertEqual(self.mnemonic, restored)


        # remove everything, restore fails
        with sdcard.filesystem(mounted=False):
            for block_num in range(io.sdcard.capacity() // io.sdcard.BLOCK_SIZE):
                io.sdcard.write(block_num, block_buffer)

        with sdcard.filesystem(mounted=False):
            restored = recover_seed_from_sdcard()
            self.assertEqual(None, restored)


if __name__ == "__main__":
    unittest.main()

from common import *

from storage.sd_seed_backup import *
from trezor import io, sdcard
from trezor.enums import BackupType


class TestStorageSdSeedBackup(unittest.TestCase):
    # TODO add more tests, also for repairing the backup card

    def setUp(self):
        self.mnemonic = (
            b"crane mesh that gain predict open dice defy lottery toddler coin upgrade"
        )

    def test_backup_and_restore(self):
        io.sdcard.power_on()
        io.fatfs.mkfs(True)
        io.fatfs.mount()

        success = store_seed_on_sdcard(self.mnemonic, BackupType.Bip39)
        self.assertTrue(success)

        restored_mnemonic, restored_backup_type = recover_seed_from_sdcard()
        self.assertEqual(restored_mnemonic, self.mnemonic)
        self.assertEqual(restored_backup_type, BackupType.Bip39)

        io.fatfs.unmount()
        io.sdcard.power_off()

    def test_backup_partlywipe_restore(self):
        with sdcard.filesystem(mounted=True):
            success = store_seed_on_sdcard(self.mnemonic, BackupType.Bip39)
            self.assertTrue(success)

        # wipe half of the card, restore must succeed
        block_buffer = bytearray(SDCARD_BLOCK_SIZE_B)
        with sdcard.filesystem(mounted=False):
            for block_num in range((io.sdcard.capacity() // 2) // io.sdcard.BLOCK_SIZE):
                io.sdcard.write(block_num, block_buffer)

        with sdcard.filesystem(mounted=False):
            restored_mnemonic, restored_backup_type = recover_seed_from_sdcard()
            self.assertEqual(restored_mnemonic, self.mnemonic)
            self.assertEqual(restored_backup_type, BackupType.Bip39)

        # remove everything, restore fails
        with sdcard.filesystem(mounted=False):
            for block_num in range(io.sdcard.capacity() // io.sdcard.BLOCK_SIZE):
                io.sdcard.write(block_num, block_buffer)

        with sdcard.filesystem(mounted=False):
            restored_mnemonic, restored_backup_type = recover_seed_from_sdcard()
            self.assertEqual(restored_mnemonic, None)
            self.assertEqual(restored_backup_type, None)


if __name__ == "__main__":
    unittest.main()

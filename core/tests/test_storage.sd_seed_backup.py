from common import *

from storage.sd_seed_backup import *
from trezor import io, sdcard
from trezor.enums import BackupType

EMPTY_BLOCK = bytes([0xFF] * io.sdcard.BLOCK_SIZE)


def erase_sdcard(portion: float = 1.0):
    """
    Helper function to erase a portion of virtual SD card.
    `portion` param is supplied in range [0.0; 1.0].

    Assumption: virtual SD card is inserted.
    """
    assert 0.0 <= portion and portion <= 1.0
    assert io.sdcard.is_present()
    with sdcard.filesystem(mounted=False):
        try:
            n_blocks = io.sdcard.capacity() // io.sdcard.BLOCK_SIZE
            for i in range(int(portion * n_blocks)):
                io.sdcard.write(i, EMPTY_BLOCK)
        except Exception:
            pass

# TODO: SLIP-39 tests

class TestStorageSdSeedBackup(unittest.TestCase):
    def setUp(self):
        self.mnemonic = (
            b"crane mesh that gain predict open dice defy lottery toddler coin upgrade"
        )

        io.sdcard_inserter.insert(1, capacity_bytes=64 * 1024 * 1024)
        io.sdcard.power_on()
        io.fatfs.mkfs(True)

        io.fatfs.mount()
        io.fatfs.unmount()

    def tearDown(self):
        erase_sdcard()
        io.sdcard.power_off()
        io.sdcard_inserter.eject()

    def test_backup_and_restore_basic(self):
        store_seed_on_sdcard(self.mnemonic, BackupType.Bip39)

        restored_mnemonic, restored_backup_type = recover_seed_from_sdcard()
        self.assertEqual(restored_mnemonic, self.mnemonic)
        self.assertEqual(restored_backup_type, BackupType.Bip39)

    def test_backup_and_restore_from_party_wiped(self):
        store_seed_on_sdcard(self.mnemonic, BackupType.Bip39)

        # wipe half of the card, restore must succeed
        erase_sdcard(portion=0.5)
        restored_mnemonic, restored_backup_type = recover_seed_from_sdcard()
        self.assertEqual(restored_mnemonic, self.mnemonic)
        self.assertEqual(restored_backup_type, BackupType.Bip39)

        # remove everything, restore fails
        erase_sdcard(portion=1.0)
        restored_mnemonic, restored_backup_type = recover_seed_from_sdcard()
        self.assertEqual(restored_mnemonic, None)
        self.assertEqual(restored_backup_type, None)

    def test_is_backup_present_on_sdcard(self):
        self.assertFalse(is_backup_present_on_sdcard())

        store_seed_on_sdcard(self.mnemonic, BackupType.Bip39)
        self.assertTrue(is_backup_present_on_sdcard())

        erase_sdcard(portion=0.9)
        self.assertTrue(is_backup_present_on_sdcard())

    def test_check_health_of_backup_sdcard(self):
        store_seed_on_sdcard(self.mnemonic, BackupType.Bip39)

        # uncorrupted backup
        health = check_health_of_backup_sdcard(self.mnemonic)
        self.assertTrue(health.pt_is_mountable)
        self.assertTrue(health.pt_has_correct_cap)
        self.assertTrue(health.pt_readme_present)
        self.assertTrue(health.pt_readme_content)
        self.assertEqual(health.unalloc_seed_corrupt, 0)

        # overwrite one seed backup
        with sdcard.filesystem(mounted=False):
            io.sdcard.write(SDBACKUP_BLOCK_START, EMPTY_BLOCK)
        health = check_health_of_backup_sdcard(self.mnemonic)
        self.assertTrue(health.pt_is_mountable)
        self.assertTrue(health.pt_has_correct_cap)
        self.assertTrue(health.pt_readme_present)
        self.assertTrue(health.pt_readme_content)
        self.assertEqual(health.unalloc_seed_corrupt, 1)

        # change the informative file in FS
        with sdcard.filesystem(mounted=True):
            with fatfs.open(README_PATH, '+') as f:
                f.write(b'abc')
        health = check_health_of_backup_sdcard(self.mnemonic)
        self.assertTrue(health.pt_is_mountable)
        self.assertTrue(health.pt_has_correct_cap)
        self.assertTrue(health.pt_readme_present)
        self.assertFalse(health.pt_readme_content)
        self.assertEqual(health.unalloc_seed_corrupt, 1)


        # remove informative file from FS
        with sdcard.filesystem(mounted=True):
            fatfs.unlink(README_PATH)
        health = check_health_of_backup_sdcard(self.mnemonic)
        self.assertTrue(health.pt_is_mountable)
        self.assertTrue(health.pt_has_correct_cap)
        self.assertFalse(health.pt_readme_present)
        self.assertFalse(health.pt_readme_content)
        self.assertEqual(health.unalloc_seed_corrupt, 1)

        # recreate FS over the whole card
        with sdcard.filesystem(mounted=False):
            fatfs.mkfs()
        health = check_health_of_backup_sdcard(self.mnemonic)
        self.assertTrue(health.pt_is_mountable)
        self.assertFalse(health.pt_has_correct_cap)
        self.assertFalse(health.pt_readme_present)
        self.assertFalse(health.pt_readme_content)
        self.assertEqual(health.unalloc_seed_corrupt, 1)

        # erase a portion of the card to destory FS partition table
        erase_sdcard(portion=0.1)
        health = check_health_of_backup_sdcard(self.mnemonic)
        self.assertFalse(health.pt_is_mountable)
        self.assertFalse(health.pt_has_correct_cap)
        self.assertFalse(health.pt_readme_present)
        self.assertFalse(health.pt_readme_content)
        self.assertEqual(health.unalloc_seed_corrupt, 1)

        # erase the whole card
        erase_sdcard(portion=1.0)
        health = check_health_of_backup_sdcard(self.mnemonic)
        self.assertFalse(health.pt_is_mountable)
        self.assertFalse(health.pt_has_correct_cap)
        self.assertFalse(health.pt_readme_present)
        self.assertFalse(health.pt_readme_content)
        self.assertEqual(health.unalloc_seed_corrupt, SDBACKUP_N_WRITINGS)

    def test_refresh_backup_sdcard(self):
        def assert_backup_health(flg: bool = True) -> None:

            health = check_health_of_backup_sdcard(self.mnemonic)
            self.assertEqual(flg, health.pt_is_mountable)
            self.assertEqual(flg, health.pt_is_mountable)
            self.assertEqual(flg, health.pt_has_correct_cap)
            self.assertEqual(flg, health.pt_readme_present)
            self.assertEqual(flg, health.pt_readme_content)
            self.assertEqual(health.unalloc_seed_corrupt, 0)

        store_seed_on_sdcard(self.mnemonic, BackupType.Bip39)
        assert_backup_health()

        # damage the backup
        erase_sdcard(portion=0.5)
        assert_backup_health(False)

        # trying to refresh with a different seed must fail
        mnemonic_faulty = (
            b"all all all all all all all all all all all all"
        )
        self.assertFalse(refresh_backup_sdcard(mnemonic_faulty))
        assert_backup_health(False)

        refresh_backup_sdcard(self.mnemonic)
        assert_backup_health()


    def test_wipe_backup_sdcard(self):
        store_seed_on_sdcard(self.mnemonic, BackupType.Bip39)
        self.assertTrue(is_backup_present_on_sdcard())

        wipe_backup_sdcard()
        self.assertFalse(is_backup_present_on_sdcard())


if __name__ == "__main__":
    unittest.main()

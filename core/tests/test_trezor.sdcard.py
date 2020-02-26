from common import *

from trezor import io, fatfs, sdcard


class TestTrezorSdcard(unittest.TestCase):
    def test_power(self):
        # sdcard.capacity() will return 0 if the card is not powered,
        # non-zero value otherwise
        self.assertEqual(sdcard.capacity(), 0)
        with sdcard.filesystem(mounted=False):
            self.assertTrue(sdcard.capacity() > 0)
        self.assertEqual(sdcard.capacity(), 0)

    def test_nomount(self):
        with sdcard.filesystem(mounted=False):
            self.assertFalse(fatfs.is_mounted())

    def test_mount(self):
        # set up a filesystem first
        with sdcard.filesystem(mounted=False):
            fatfs.mkfs()

        with sdcard.filesystem():
            self.assertTrue(fatfs.is_mounted())

        self.assertFalse(fatfs.is_mounted())

    def test_nesting(self):
        # set up a filesystem first
        with sdcard.filesystem(mounted=False):
            fatfs.mkfs()

        self.assertEqual(sdcard.capacity(), 0)
        with sdcard.filesystem():
            self.assertTrue(sdcard.capacity() > 0)
            self.assertTrue(fatfs.is_mounted())
            with sdcard.filesystem():
                self.assertTrue(sdcard.capacity() > 0)
                self.assertTrue(fatfs.is_mounted())

            self.assertTrue(sdcard.capacity() > 0)
            self.assertTrue(fatfs.is_mounted())

        self.assertEqual(sdcard.capacity(), 0)
        self.assertFalse(fatfs.is_mounted())

    def test_mount_nomount(self):
        with self.assertRaises(RuntimeError):
            with sdcard.filesystem(mounted=True):
                with sdcard.filesystem(mounted=False):
                    pass

        with self.assertRaises(RuntimeError):
            with sdcard.filesystem(mounted=False):
                with sdcard.filesystem(mounted=True):
                    pass

    def test_failed_mount(self):
        # set up a filesystem first
        with sdcard.filesystem(mounted=False):
            fatfs.mkfs()

        with sdcard.filesystem():
            self.assertTrue(fatfs.is_mounted())

        # trash filesystem
        io.sdcard.power_on()
        io.sdcard.write(0, bytes([0xFF] * io.sdcard.BLOCK_SIZE))
        io.sdcard.power_off()

        # mounting should now fail
        with self.assertRaises(OSError):
            with sdcard.filesystem():
                pass

        self.assertFalse(fatfs.is_mounted())

        # it should be possible to create an unmounted instance
        with sdcard.filesystem(mounted=False):
            fatfs.mkfs()

        # mounting should now succeed
        with sdcard.filesystem():
            self.assertTrue(fatfs.is_mounted())


if __name__ == "__main__":
    unittest.main()

from common import *

from trezor import io, sdcard


class TestTrezorSdcard(unittest.TestCase):
    def test_power(self):
        # io.sdcard.capacity() will return 0 if the card is not powered,
        # non-zero value otherwise
        self.assertEqual(io.sdcard.capacity(), 0)
        with sdcard.get_filesystem(mounted=False):
            self.assertTrue(io.sdcard.capacity() > 0)
        self.assertEqual(io.sdcard.capacity(), 0)

    def test_nomount(self):
        with sdcard.get_filesystem(mounted=False) as fs:
            with self.assertRaises(OSError):
                fs.listdir("/")

    def test_mount(self):
        # set up a filesystem first
        with sdcard.get_filesystem(mounted=False) as fs:
            fs.mkfs()

        with sdcard.get_filesystem() as fs:
            # the following should succeed
            fs.listdir("/")

        # filesystem should not be available
        with self.assertRaises(OSError):
            fs.listdir("/")

    def test_nesting(self):
        # set up a filesystem first
        with sdcard.get_filesystem(mounted=False) as fs:
            fs.mkfs()

        self.assertEqual(io.sdcard.capacity(), 0)
        with sdcard.get_filesystem() as fs_a:
            self.assertTrue(io.sdcard.capacity() > 0)
            with sdcard.get_filesystem() as fs_b:
                self.assertTrue(io.sdcard.capacity() > 0)
                self.assertIs(fs_a, fs_b)
                fs_b.listdir("/")
            self.assertTrue(io.sdcard.capacity() > 0)
            # filesystem should still be mounted
            fs_a.listdir("/")

        self.assertEqual(io.sdcard.capacity(), 0)
        # filesystem should not be available
        with self.assertRaises(OSError):
            fs_a.listdir("/")

    def test_mount_nomount(self):
        with self.assertRaises(RuntimeError):
            with sdcard.get_filesystem(mounted=True):
                with sdcard.get_filesystem(mounted=False):
                    pass

        with self.assertRaises(RuntimeError):
            with sdcard.get_filesystem(mounted=False):
                with sdcard.get_filesystem(mounted=True):
                    pass

    def test_failed_mount(self):
        # set up a filesystem first
        with sdcard.get_filesystem(mounted=False) as fs:
            fs.mkfs()

        with sdcard.get_filesystem() as fs:
            # the following should succeed
            fs.listdir("/")

        # trash filesystem
        io.sdcard.power_on()
        io.sdcard.write(0, bytes([0xFF] * io.sdcard.BLOCK_SIZE))
        io.sdcard.power_off()

        # mounting should now fail
        with self.assertRaises(OSError):
            with sdcard.get_filesystem() as fs:
                pass

        # it should be possible to create an unmounted instance
        with sdcard.get_filesystem(mounted=False) as fs:
            fs.mkfs()

        # mounting should now succeed
        with sdcard.get_filesystem() as fs:
            fs.listdir("/")



if __name__ == "__main__":
    unittest.main()

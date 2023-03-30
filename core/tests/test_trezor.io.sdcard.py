from common import *

from trezor import io


class TestTrezorIoSdcard(unittest.TestCase):

    def test_start(self):
        self.assertTrue(io.sdcard.is_present())

    def test_power(self):
        x = bytearray(8 * 512)
        self.assertEqual(io.sdcard.capacity(), 0)
        with self.assertRaises(OSError):
            io.sdcard.read(0, x)
        io.sdcard.power_on()
        self.assertTrue(io.sdcard.capacity() > 0)
        io.sdcard.read(0, x)
        io.sdcard.power_off()
        self.assertEqual(io.sdcard.capacity(), 0)
        with self.assertRaises(OSError):
            io.sdcard.read(0, x)

    def test_read(self):
        x = bytearray(8 * 512)
        io.sdcard.power_on()
        io.sdcard.read(0, x)
        io.sdcard.power_off()
        with self.assertRaises(OSError):
            io.sdcard.read(0, x)

    def test_read_write(self):
        r = bytearray(8 * 512)
        w0 = bytearray(b'0' * (8 * 512))
        w1 = bytearray(b'1' * (8 * 512))
        io.sdcard.power_on()
        io.sdcard.write(0, w0)
        io.sdcard.read(0, r)
        self.assertEqual(r, w0)
        io.sdcard.write(0, w1)
        io.sdcard.read(0, r)
        self.assertEqual(r, w1)
        io.sdcard.power_off()


if __name__ == '__main__':
    unittest.main()

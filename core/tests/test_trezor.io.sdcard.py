from common import *

from trezor import io


class TestTrezorIoSdcard(unittest.TestCase):

    def test_start(self):
        sd = io.SDCard()
        self.assertTrue(sd.present())

    def test_power(self):
        sd = io.SDCard()
        x = bytearray(8 * 512)
        self.assertEqual(sd.capacity(), 0)
        self.assertFalse(sd.read(0, x))
        sd.power(True)
        self.assertTrue(sd.capacity() > 0)
        self.assertTrue(sd.read(0, x))
        sd.power(False)
        self.assertEqual(sd.capacity(), 0)
        self.assertFalse(sd.read(0, x))

    def test_read(self):
        sd = io.SDCard()
        x = bytearray(8 * 512)
        sd.power(True)
        self.assertTrue(sd.read(0, x))
        sd.power(False)
        self.assertFalse(sd.read(0, x))

    def test_read_write(self):
        sd = io.SDCard()
        r = bytearray(8 * 512)
        w0 = bytearray(b'0' * (8 * 512))
        w1 = bytearray(b'1' * (8 * 512))
        sd.power(True)
        self.assertTrue(sd.write(0, w0))
        self.assertTrue(sd.read(0, r))
        self.assertEqual(r, w0)
        self.assertTrue(sd.write(0, w1))
        self.assertTrue(sd.read(0, r))
        self.assertEqual(r, w1)
        sd.power(False)


if __name__ == '__main__':
    unittest.main()

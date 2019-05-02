from common import unittest

from trezor import io


class TestIo(unittest.TestCase):

    def test_sdcard_start(self):
        sd = io.SDCard()
        assert sd.present() is True

    def test_sdcard_power(self):
        sd = io.SDCard()
        x = bytearray(8 * 512)
        assert sd.capacity() == 0
        assert sd.read(0, x) is False
        sd.power(True)
        assert sd.capacity() > 0
        assert sd.read(0, x) is True
        sd.power(False)
        assert sd.capacity() == 0
        assert sd.read(0, x) is False

    def test_sdcard_read(self):
        sd = io.SDCard()
        x = bytearray(8 * 512)
        sd.power(True)
        assert sd.read(0, x) is True
        sd.power(False)
        assert sd.read(0, x) is False

    def test_sdcard_read_write(self):
        sd = io.SDCard()
        r = bytearray(8 * 512)
        w0 = bytearray(b'0' * (8 * 512))
        w1 = bytearray(b'1' * (8 * 512))
        sd.power(True)
        assert sd.write(0, w0) is True
        assert sd.read(0, r) is True
        assert r == w0
        assert sd.write(0, w1) is True
        assert sd.read(0, r) is True
        assert r == w1
        sd.power(False)


if __name__ == '__main__':
    unittest.main()

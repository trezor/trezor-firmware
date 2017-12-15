from common import *

from trezor import io


class TestIo(unittest.TestCase):

    def test_sdcard_start(self):
        sd = io.SDCard()
        assert sd.present() == True

    def test_sdcard_power(self):
        sd = io.SDCard()
        x = bytearray(8 * 512)
        assert sd.capacity() == 0
        assert sd.read(0, x) == False
        sd.power(True)
        assert sd.capacity() > 0
        assert sd.read(0, x) == True
        sd.power(False)
        assert sd.capacity() == 0
        assert sd.read(0, x) == False

    def test_sdcard_read(self):
        sd = io.SDCard()
        x = bytearray(8 * 512)
        sd.power(True)
        assert sd.read(0, x) == True
        sd.power(False)
        assert sd.read(0, x) == False

    def test_sdcard_read_write(self):
        sd = io.SDCard()
        r = bytearray(8 * 512)
        w0 = bytearray(b'0' * (8 * 512))
        w1 = bytearray(b'1' * (8 * 512))
        sd.power(True)
        assert sd.write(0, w0) == True
        assert sd.read(0, r) == True
        assert r == w0
        assert sd.write(0, w1) == True
        assert sd.read(0, r) == True
        assert r == w1
        sd.power(False)


if __name__ == '__main__':
    unittest.main()

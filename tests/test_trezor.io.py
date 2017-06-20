from common import *

from trezor import io

class TestIo(unittest.TestCase):

    def test_sdcard(self):
        sd = io.SDCard()
        sd.present()

if __name__ == '__main__':
    unittest.main()

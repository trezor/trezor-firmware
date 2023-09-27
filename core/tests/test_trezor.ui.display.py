from common import *

from trezor.ui import display


class TestDisplay(unittest.TestCase):

    def test_refresh(self):
        display.refresh()

    def test_bar(self):
        display.bar(0, 0, 10, 10, 0xFFFF)

    def test_orientation(self):
        for o in [0, 90, 180, 270]:
            display.orientation(o)

    def test_backlight(self):
        for b in range(256):
            display.backlight(b)

    def test_raw(self):
        pass

    def test_save(self):
        pass


if __name__ == '__main__':
    unittest.main()
